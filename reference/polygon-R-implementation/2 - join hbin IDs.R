# Joins hbin IDs to ebd observations

# load packages
library(tidyverse)

join_hbins <- function(hbins, obs) {
  # add ID column
  hbins <- hbins %>%
    mutate(id = row_number())
  
  # filter observations to hbin extent
  obs_aoi <- st_filter(obs, hbins)
  
  # join hbin ID to every observation for each hbin level
  levels = unique(hbins$level)
  for (l in levels) {
    obs_aoi <- obs_aoi %>% 
      st_join(filter(hbins, level == l) %>% 
                select(-level), join=st_within) %>% 
      rename_with(.fn = ~paste0('level',l), .cols=c("id"))
  }
  dataset <- list(hbins=hbins, obs=obs_aoi)
  return(dataset)
}