# Computes scale variance

# load packages
library(tidyverse)
library(sf)
library(lazyeval)
library(glue)
library(egg)
library(scales)

compute_scale_variance <- function(hbins_estD, hbins) {
  
  # create table data frame with hbin IDs per level
  df <- hbins_estD %>%
    select(id, estD) %>%
    rename(id_level1 = id, estD_level1 = estD)
  
  # define function to join parent bins for a specified bin level
  join_parent_bins <- function(leveln) {
    return(
      st_join(
        df,
        filter(hbins_estD, level == leveln) %>% select(id),
        join = st_within,
        left = TRUE,
        suffix = c("_X", paste0("_level", leveln))
      ) %>%
        st_drop_geometry() %>%
        select(id) %>%
        rename_with(~paste0(.x, "_level", leveln))
    )
  }
  
  # specify list of levels
  levels <- hbins$level %>% unique() %>% as.numeric()
  
  # join parent bins for specified levels (all except level 1)
  df <- levels[-1] %>%
    map_dfc(join_parent_bins) %>%
    bind_cols(df, .)
  
  # remove level 1 bins with no value
  df <- df %>%
    filter(!is.na(estD_level1))
  
  # drop geometry
  df <- df %>% 
    st_drop_geometry()
  
  # add column for final level (global value)
  df <- df %>%
    mutate("id_level{max(levels)+1}" := max(hbins_estD$id)+1,
           "estD_level{max(levels)+1}" := mean(estD_level1))
  
  # define function to compute bin value (mean of bins from level below) for a
  # specified level
  compute_level_mean <- function(leveln) {
    df <<- df %>%
      group_by(!!sym(glue("id_level{leveln}"))) %>%
      summarise("estD_level{leveln}" := 
                  mean(!!sym(glue("estD_level{leveln-1}")))) %>%
      left_join(df, .)
  }
  
  # compute bin values for all levels except level 1
  r <- levels[-1] %>%
    map(compute_level_mean)
  
  # define function to compute squared differences between leveln and leveln+1
  compute_squares <- function(leveln) {
    return(
      df %>%
        transmute("sq_level{leveln}" := 
                    (!!sym(glue("estD_level{leveln+1}")) - 
                       !!sym(glue("estD_level{leveln}")))^2)
    )
  }
  
  # compute sum of squares for all levels
  ss <- levels %>%
    map_dfc(compute_squares) %>%
    summarise(across(everything(), ~ sum(.)))
  
  # define function to compute degrees of freedom for leveln
  compute_degf <- function(leveln) {
    return(
      df %>%
        group_by(!!sym(glue("id_level{leveln+1}"))) %>%
        summarize(count = n_distinct(!!sym(glue("id_level{leveln}")))) %>%
        mutate(degf_ = count - 1) %>%
        pull(degf_) %>%
        sum
    )
  }
  
  # define function to compute degrees of freedom for all levels
  degf <- levels %>%
    map(compute_degf)
  
  # define function to compute scale variance elements for leveln
  compute_sv_elements <- function(leveln) {
    return(
      df %>% 
        group_by(!!sym(glue("id_level{leveln}"))) %>%
        summarise(col1 = mean(!!sym(glue("estD_level{leveln}"))), 
                  col2 = mean(!!sym(glue("estD_level{leveln+1}")))) %>%
        mutate(sv = ((col2-col1)^2)) %>% 
        mutate(sv_n = sv/compute_degf(leveln)) %>% 
        rename(id = !!sym(glue("id_level{leveln}"))) %>% 
        left_join(hbins, by = c("id" = "id"), keep = FALSE) %>% 
        st_as_sf()
    )
  }
  
  # define function to compute scale variance component for leveln
  compute_sv_component <- function(leveln) {
    return(
      sve[[leveln]] %>% 
        pull(sv) %>% 
        sum/compute_degf(leveln)
    )
  }
  
  # compute scale variance elements for all levels
  sve <- levels %>% map(compute_sv_elements)
  
  # compute scale variance component for all levels
  svc <- levels %>%
    map(compute_sv_component) %>%
    as.numeric() %>%
    tibble(
      scale_variance = .,
      level = levels
    )
  
  # compute total sum of squares
  tss <- sum((df[["estD_level1"]] - df[[glue("estD_level{max(levels)+1}")]])^2)
  
  # compute total degrees of freedom
  tdegf <- df %>% nrow()-1
  
  # define function to compute list of scales from size of the level1 scale and
  # the total number of levels
  compute_scales <- function(start, nlevels) {
    scales <- c(1:nlevels) %>% map(~start*2^(.x-1))
    return(as.numeric(scales))
  }
  
  # transform scale variance components to percent of total 
  # (where sum of all = 1)
  svc_p <- svc %>% 
    mutate(scale_variance = scale_variance/sum(svc$scale_variance),
           scale = compute_scales(hbins %>% 
                                    filter(level == 1) %>% 
                                    first() %>% 
                                    st_area(.$geometry) %>% 
                                    sqrt(), 
                                  length(levels)),
           sv_cumulative = cumsum(scale_variance),
           degf = as.numeric(degf),
           sum_squares = as.numeric(ss)
    )
  
  # define function to rejoin geometry to estD values for a specified level
  join_estD_value_geometry <- function(leveln) {
    return(
      df %>% 
        select(!!sym(glue("id_level{leveln}")), !!sym(glue("estD_level{leveln}"))) %>% 
        rename(id = !!sym(glue("id_level{leveln}")), estD = !!sym(glue("estD_level{leveln}"))) %>% 
        inner_join(hbins, ., by = c("id" = "id"), multiple="any", keep = FALSE, unmatched = "drop")
    )
  }
  # compute scale variance elements for all levels
  estD_values <- levels %>% map_df(join_estD_value_geometry) %>% st_as_sf()
  
  sv_result <- list(sve = sve, svc = svc_p, ss = ss, tss = tss, degf = degf, estD_values = estD_values)
  
  return(sv_result)
}
