# Load necessary libraries
# Ensure terra, dplyr, and tibble are installed:
# install.packages(c("terra", "dplyr", "tibble"))
library(terra)
library(dplyr)
library(tibble)

#' Compute Scale Variance for Raster Data
#'
#' @description
#' Performs scale variance analysis on a raster dataset by aggregating cells
#' across multiple levels and calculating variance components at each scale,
#' following the principles outlined in ANOVA for hierarchical spatial data.
#' The percentage of variance reported is based on the contribution of each
#' level's Sum of Squares to the Total Sum of Squares, matching the method
#' used in Moellering & Tobler (1972).
#'
#' @param rast A terra SpatRaster object with a single layer. The analysis will
#'   be performed on this layer.
#' @param num_levels (Optional) Integer. The desired number of aggregation levels,
#'   including the original resolution (level 1). If NULL (default), the maximum
#'   possible number of levels based on `base_level_factor` and raster dimensions
#'   is calculated automatically.
#' @param base_level_factor Integer. The aggregation factor used at each step to
#'   define the next coarser level (default: 2, i.e., doubling the linear cell dimension).
#'   Aggregation occurs by a factor of `base_level_factor` in both x and y directions.
#' @param agg_fun Function or character string. The function used for aggregation
#'   when creating coarser levels (e.g., "mean", "sum", "median"). Default is "mean".
#' @param na_rm Logical. Whether to remove NA values during the aggregation process
#'   (`terra::aggregate`). Default is TRUE. Note: The analysis itself is performed
#'   only on cells that have a non-NA value at the finest resolution (level 1).
#' @param output_vars Character vector. Specifies which results to include in the
#'   output list. Possible values:
#'   - "svc": (Default) Scale Variance Components summary table (tibble).
#'   - "sve": Scale Variance Elements (SpatRaster with layers for squared differences).
#'   - "tss": (Default) Total Sum of Squares (numeric).
#'   - "tdf": (Default) Total Degrees of Freedom (numeric).
#'   - "level_rasters": List of aggregated SpatRaster objects for each level.
#'   - "details": Data frame used for internal calculations (values per original cell per level).
#'   Default is c("svc", "tss", "tdf").
#'
#' @return A list containing the requested scale variance analysis results.
#'   - svc: A tibble with columns:
#'     - level: The aggregation level (1 = finest).
#'     - scale: The mean resolution (cell size) at this level.
#'     - sum_squares: Sum of Squares comparing level l to level l+1.
#'     - degf: Degrees of freedom for the sum_squares at this level.
#'     - mean_square: Mean Square (sum_squares / degf).
#'     - ss_p: Proportion of the Total Sum of Squares (TSS) accounted for by this level.
#'     - ss_cumulative_p: Cumulative proportion of TSS accounted for up to this level.
#'   - sve: A SpatRaster object with `num_levels` layers. Each layer `i` represents the
#'          squared difference between the value at level `i` and level `i+1` for each
#'          original cell location.
#'   - tss: Numeric value of the total sum of squares relative to the global mean.
#'   - tdf: Numeric value of the total degrees of freedom (N-1, where N is the
#'          number of non-NA cells at level 1).
#'   - level_rasters: List of SpatRaster objects, where element `i` is the raster
#'                    aggregated to level `i`.
#'   - details: Data frame with columns `value_level1`, `value_level2`, ...,
#'              `value_level<num_levels+1>` (global mean), containing the corresponding
#'              value for each original non-NA cell.
#'
#' @import terra
#' @import dplyr
#' @import tibble
#' @export
#'
#' @examples
#' \dontrun{
#' # Load required packages for examples
#' library(terra)
#' library(dplyr)
#' library(tibble)
#' library(readr) # For reading the example CSV
#' library(here)  # For relative paths if running example 4
#'
#' # Create a sample raster with spatial pattern and NAs
#' r <- rast(nrows=64, ncols=64, xmin=0, xmax=64, ymin=0, ymax=64, crs="local")
#' xy <- xyFromCell(r, 1:ncell(r))
#' values(r) <- sin(xy[,1]/5) * cos(xy[,2]/5) * 100 + rnorm(ncell(r), 0, 20)
#' r[sample(ncell(r), 500)] <- NA # Add some NAs
#'
#' plot(r, main="Original Raster Data")
#'
#' # --- Example 1: Basic analysis with automatic levels ---
#' sv_results_auto <- compute_scale_variance_raster(r)
#' print("--- SVC Table (Auto Levels) ---")
#' print(sv_results_auto$svc)
#' print(paste("TSS:", round(sv_results_auto$tss, 2)))
#' print(paste("TDF:", sv_results_auto$tdf))
#'
#' # Plot the results based on SS percentages
#' if (!is.null(sv_results_auto$svc) && nrow(sv_results_auto$svc) > 0) {
#'   plot(sv_results_auto$svc$scale, sv_results_auto$svc$ss_p,
#'        type='b', log='x', pch=16, ylim=c(0, max(sv_results_auto$svc$ss_p, na.rm=TRUE)*1.1),
#'        xlab="Scale (Mean Resolution)", ylab="Proportion of Total Sum of Squares",
#'        main="Scale Variance Analysis (based on SS)")
#'   lines(sv_results_auto$svc$scale, sv_results_auto$svc$ss_cumulative_p, type='b', pch=1, col='blue')
#'   abline(h=0, lty=2, col='grey')
#'   legend("topleft", legend=c("SS Proportion (%)", "Cumulative SS Proportion (%)"),
#'          pch=c(16, 1), col=c("black", "blue"), lty=1, bty="n")
#' }
#'
#' # --- Example 2: Specify levels and request SVE ---
#' sv_results_sve <- compute_scale_variance_raster(r, num_levels = 4,
#'                                                output_vars = c("svc", "sve", "tss"))
#' print("--- SVC Table (4 Levels) ---")
#' print(sv_results_sve$svc)
#'
#' if (!is.null(sv_results_sve$sve)) {
#'   plot(sv_results_sve$sve, main="Scale Variance Elements (Squared Differences)")
#' }
#'
#' # --- Example 3: Using 'sum' aggregation ---
#' sv_results_sum <- compute_scale_variance_raster(r, agg_fun = "sum")
#' print("--- SVC Table (Aggregation: sum) ---")
#' print(sv_results_sum$svc)
#'
#' # --- Example 4: Using Fig3 from Moellering and Tobler 1972 ---
#' # Create a dummy CSV file for the example if it doesn't exist
#' fig3_csv_path <- "Fig3_MT1972.csv"
#' if (!file.exists(fig3_csv_path)) {
#'   fig3_mat_data <- matrix(c(
#'     2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
#'     5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
#'     2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
#'     5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
#'     2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
#'     5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
#'     2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
#'     5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
#'     5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
#'     8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
#'     5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
#'     8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
#'     5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
#'     8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
#'     5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
#'     8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2
#'   ), nrow = 16, ncol = 16, byrow = TRUE)
#'   write.table(fig3_mat_data, fig3_csv_path, sep = ",", row.names = FALSE, col.names = FALSE)
#'   message("Created dummy Fig3_MT1972.csv for example 4.")
#' }
#'
#' # Check if the file exists before reading
#' if (file.exists(fig3_csv_path)) {
#'   fig3_matrix <- as.matrix(read_csv(fig3_csv_path, col_names = FALSE, col_types = cols(.default = col_double())))
#'   fig3_raster <- rast(fig3_matrix)
#'   # Set extent for scale calculation (assuming unit cells)
#'   ext(fig3_raster) <- c(0, ncol(fig3_raster), 0, nrow(fig3_raster))
#'   crs(fig3_raster) <- "local" # Assign a CRS
#'
#'   fig3_sv_results <- compute_scale_variance_raster(fig3_raster, output_vars = c("svc", "tss", "tdf"))
#'   print("--- SVC Table (Moellering & Tobler 1972 Fig 3 Data) ---")
#'   print(fig3_sv_results$svc)
#'   print(paste("TSS:", fig3_sv_results$tss)) # Should be 1152
#'   print(paste("TDF:", fig3_sv_results$tdf)) # Should be 255
#'
#'   # Plot results for Example 4
#'   if (!is.null(fig3_sv_results$svc) && nrow(fig3_sv_results$svc) > 0) {
#'      plot(fig3_sv_results$svc$scale, fig3_sv_results$svc$ss_p,
#'           type='b', log='x', pch=16, ylim=c(0, max(fig3_sv_results$svc$ss_p, na.rm=TRUE)*1.1),
#'           xlab="Scale (Mean Resolution)", ylab="Proportion of Total Sum of Squares",
#'           main="Scale Variance Analysis (M&T Fig 3 - based on SS)")
#'      lines(fig3_sv_results$svc$scale, fig3_sv_results$svc$ss_cumulative_p, type='b', pch=1, col='blue')
#'      abline(h=0, lty=2, col='grey')
#'      legend("topleft", legend=c("SS Proportion (%)", "Cumulative SS Proportion (%)"),
#'             pch=c(16, 1), col=c("black", "blue"), lty=1, bty="n")
#'   }
#'
#' } else {
#'   warning("Could not find ", fig3_csv_path, " to run Example 4.")
#' }
#'
#' } # End dontrun
compute_scale_variance_raster <- function(rast,
                                          num_levels = NULL,
                                          base_level_factor = 2,
                                          agg_fun = "mean",
                                          na_rm = TRUE,
                                          output_vars = c("svc", "tss", "tdf")) {
  
  # --- Input Validation ---
  if (!inherits(rast, "SpatRaster")) {
    stop("Input 'rast' must be a SpatRaster object.")
  }
  if (nlyr(rast) != 1) {
    warning("Input 'rast' has multiple layers. Using the first layer only.")
    rast <- rast[[1]] # Select the first layer
  }
  if (!is.numeric(base_level_factor) || base_level_factor < 2 || base_level_factor != floor(base_level_factor)) {
    stop("'base_level_factor' must be an integer >= 2.")
  }
  # Check if agg_fun is a function or a recognized character string
  if (!is.function(agg_fun) && !is.character(agg_fun)) {
    stop("'agg_fun' must be a function or a character string (e.g., 'mean').")
  }
  if (is.character(agg_fun)) {
    # Basic check for common functions, terra handles others
    if (!agg_fun %in% c("mean", "sum", "min", "max", "median", "modal", "sd", "var")) {
      warning("Provided 'agg_fun' string ('", agg_fun, "') is not a standard aggregation function. Ensure terra::aggregate supports it.")
    }
  }
  # Check output_vars
  valid_outputs <- c("svc", "sve", "tss", "tdf", "level_rasters", "details")
  if (!all(output_vars %in% valid_outputs)) {
    invalid_vars <- output_vars[!output_vars %in% valid_outputs]
    stop("Invalid 'output_vars' specified: ", paste(invalid_vars, collapse=", "))
  }
  
  # --- Determine Number of Levels ---
  res_xy <- res(rast)
  dims <- dim(rast)[1:2] # rows, cols
  
  # Calculate max aggregation factor possible based on smallest dimension
  max_fact <- min(dims)
  
  # Calculate the maximum number of levels based on the aggregation factor
  # Level 1 is the original raster.
  # Ensure log base is valid
  if (base_level_factor <= 1) stop("base_level_factor must be > 1 for logarithmic calculation.")
  max_possible_levels <- floor(log(max_fact, base = base_level_factor)) + 1
  
  if (is.null(num_levels)) {
    num_levels <- max_possible_levels
    message(paste("Automatically determined number of levels:", num_levels))
  } else {
    # Validate user-provided num_levels
    if (!is.numeric(num_levels) || num_levels < 1 || num_levels != floor(num_levels)) {
      stop("'num_levels' must be a positive integer.")
    }
    if (num_levels > max_possible_levels) {
      warning(paste("Requested 'num_levels' (", num_levels, ") exceeds maximum possible (",
                    max_possible_levels, "). Setting to maximum.", sep=""))
      num_levels <- max_possible_levels
    }
    # Handle the case where only 1 level is possible or requested
    if (num_levels <= 1) {
      warning("Only 1 level specified or possible. Scale variance analysis requires at least 2 levels. Returning minimal info.")
      res0 <- mean(res_xy) # Mean resolution
      n_valid <- sum(!is.na(values(rast, na.rm=FALSE)))
      # Adjusted SVC table for single level
      svc <- tibble(level = 1, scale = res0, sum_squares = NA_real_, degf = NA_integer_,
                    mean_square = NA_real_, ss_p = NA_real_, ss_cumulative_p = NA_real_)
      results <- list()
      if ("svc" %in% output_vars) results$svc <- svc
      if ("tss" %in% output_vars) results$tss <- 0 # No variation across scales
      if ("tdf" %in% output_vars) results$tdf <- max(0, n_valid - 1)
      if ("level_rasters" %in% output_vars) results$level_rasters <- list(level_1 = rast)
      return(results)
    }
  }
  
  # --- Aggregation Loop ---
  message("Aggregating raster across levels...")
  level_rasters <- vector("list", num_levels)
  level_rasters[[1]] <- rast
  names(level_rasters)[1] <- "level_1"
  
  # Aggregate iteratively
  for (level in 2:num_levels) {
    # Aggregate the *previous* level's raster by the base factor
    agg_factor <- base_level_factor
    prev_rast <- level_rasters[[level - 1]]
    
    # Check if further aggregation is possible given dimensions
    current_dims <- dim(prev_rast)[1:2]
    if(any(current_dims < agg_factor)){
      warning(paste("Cannot aggregate further at level", level, "due to raster dimensions (",
                    current_dims[1], "x", current_dims[2], ") being smaller than factor (", agg_factor,
                    "). Stopping at level", level-1))
      num_levels <- level - 1 # Adjust the number of levels processed
      level_rasters <- level_rasters[1:num_levels] # Trim the list
      # Check again if we have enough levels for analysis
      if (num_levels <= 1) {
        warning("Only 1 level possible after dimension check. Scale variance analysis requires at least 2 levels. Returning minimal info.")
        res0 <- mean(res_xy)
        n_valid <- sum(!is.na(values(rast, na.rm=FALSE)))
        svc <- tibble(level = 1, scale = res0, sum_squares = NA_real_, degf = NA_integer_,
                      mean_square = NA_real_, ss_p = NA_real_, ss_cumulative_p = NA_real_)
        results <- list()
        if ("svc" %in% output_vars) results$svc <- svc
        if ("tss" %in% output_vars) results$tss <- 0
        if ("tdf" %in% output_vars) results$tdf <- max(0, n_valid - 1)
        if ("level_rasters" %in% output_vars) results$level_rasters <- list(level_1 = rast)
        return(results)
      }
      break # Exit the loop
    }
    
    # Perform aggregation
    current_rast <- tryCatch({
      terra::aggregate(prev_rast, fact = agg_factor, fun = agg_fun, na.rm = na_rm)
    }, error = function(e) {
      stop("Error during terra::aggregate at level ", level, ": ", e$message)
    })
    
    level_rasters[[level]] <- current_rast
    names(level_rasters)[level] <- paste0("level_", level)
  }
  message(paste("Aggregation complete. Processed", num_levels, "levels."))
  
  # --- Extract Values and Align ---
  message("Extracting and aligning values across levels...")
  all_level_values <- vector("list", num_levels)
  rast_template <- rast # Use original raster as template for alignment and NA positions
  
  # Get indices of original cells that have valid data at level 1
  valid_cell_idx <- which(!is.na(values(rast_template, na.rm=FALSE)))
  n_valid_cells <- length(valid_cell_idx)
  
  if(n_valid_cells == 0) {
    stop("Input raster contains only NA values at the finest resolution.")
  }
  
  # Get values for level 1
  all_level_values[[1]] <- values(rast_template, na.rm=FALSE)[valid_cell_idx]
  
  # Get values for subsequent levels, aligned to original cells
  for (level in 2:num_levels) {
    # Disaggregate the coarser raster back to the original resolution
    # The total aggregation factor relative to level 1 is base_level_factor^(level-1)
    total_agg_factor <- base_level_factor^(level - 1)
    
    # Use disaggregate (faster for integer factors)
    # Ensure the aggregated raster has values before disaggregating
    if(all(is.na(values(level_rasters[[level]], na.rm=FALSE)))) {
      warning("Aggregated raster at level ", level, " contains only NA values. Check aggregation function and na.rm setting.")
      # Create a raster of NAs with the right dimensions for resampling
      disagg_rast <- rast(level_rasters[[level]]) # Get structure
      values(disagg_rast) <- NA
      ext(disagg_rast) <- ext(level_rasters[[level]]) # Ensure extent is correct
      disagg_rast <- terra::disagg(disagg_rast, fact = total_agg_factor, method = "near")
      
    } else {
      disagg_rast <- terra::disagg(level_rasters[[level]], fact = total_agg_factor, method = "near")
    }
    
    # Resample to ensure perfect alignment and extent matching the original grid
    # 'near' assigns the value from the nearest coarser cell center
    # Ensure rast_template has a CRS if disagg_rast does (or vice versa)
    if(is.na(crs(rast_template)) && !is.na(crs(disagg_rast))) {
      crs(rast_template) <- crs(disagg_rast) # Assign CRS for compatibility
      warning("Assigned CRS from aggregated raster to template raster for resampling.")
    } else if (!is.na(crs(rast_template)) && is.na(crs(disagg_rast))) {
      crs(disagg_rast) <- crs(rast_template)
      warning("Assigned CRS from template raster to disaggregated raster for resampling.")
    }
    
    resampled_rast <- terra::resample(disagg_rast, rast_template, method = "near")
    
    # Extract values only for the originally valid cells
    all_level_values[[level]] <- values(resampled_rast, na.rm=FALSE)[valid_cell_idx]
  }
  message("Value extraction complete.")
  
  # --- Prepare Data Frame for Calculations ---
  # Combine the lists of values into a data frame
  df_values <- as.data.frame(do.call(cbind, all_level_values))
  colnames(df_values) <- paste0("value_level", 1:num_levels)
  
  # Add the global mean as the value for the "next" level (level num_levels + 1)
  # Calculate global mean only from valid level 1 cells
  global_mean <- base::mean(df_values$value_level1, na.rm = TRUE) # Should be safe as NAs are excluded
  df_values[[paste0("value_level", num_levels + 1)]] <- global_mean
  
  # --- Compute Sum of Squares (SS) per Level ---
  message("Calculating Sum of Squares...")
  ss_list <- lapply(1:num_levels, function(level) {
    # Squared difference between value at level l+1 and level l
    sq_diff <- (df_values[[paste0("value_level", level + 1)]] - df_values[[paste0("value_level", level)]])^2
    # Sum across all valid original cells
    sum(sq_diff, na.rm = TRUE) # NAs shouldn't be present here if logic holds
  })
  ss_vec <- as.numeric(ss_list)
  
  # --- Compute Degrees of Freedom (df) per Level ---
  # df for level 'l' corresponds to the variation explained when moving
  # from level 'l' to level 'l+1'. It's based on the reduction in
  # the number of independent spatial units (aggregated cells with data).
  message("Calculating Degrees of Freedom...")
  num_cells_list <- lapply(level_rasters, function(r) {
    # Count non-NA cells in each *aggregated* raster
    sum(!is.na(values(r, na.rm = FALSE)))
  })
  
  degf_list <- vector("list", num_levels)
  for (level in 1:(num_levels - 1)) {
    # df = (number of non-NA cells at level l) - (number of non-NA cells at level l+1)
    # Ensure counts are valid numbers before subtracting
    n_l <- num_cells_list[[level]]
    n_l_plus_1 <- num_cells_list[[level + 1]]
    if (is.na(n_l) || is.na(n_l_plus_1)) {
      degf_list[[level]] <- NA_integer_
      warning("NA encountered in non-NA cell counts for df calculation at level ", level)
    } else {
      degf_list[[level]] <- n_l - n_l_plus_1
    }
  }
  # df for the last level comparison (level N vs global mean = 1 unit)
  n_last <- num_cells_list[[num_levels]]
  if (is.na(n_last)) {
    degf_list[[num_levels]] <- NA_integer_
    warning("NA encountered in non-NA cell counts for df calculation at level ", num_levels)
  } else {
    degf_list[[num_levels]] <- n_last - 1 # Subtract 1 for the global mean comparison
  }
  
  
  # Ensure df is not negative (can happen if aggregation adds NAs unexpectedly)
  degf_list <- lapply(degf_list, function(x) if(is.na(x)) NA_integer_ else max(0, x))
  degf_vec <- as.numeric(degf_list)
  
  # --- Compute Total Sum of Squares (TSS) and Total df (TDF) ---
  # TSS: Variation of level 1 values around the global mean
  tss <- sum((df_values$value_level1 - global_mean)^2, na.rm = TRUE)
  # TDF: Number of valid cells at level 1 minus 1
  tdf <- n_valid_cells - 1
  
  # --- Sanity Checks ---
  # Check if sum of SS across levels approximately equals TSS
  # Allow a small tolerance (e.g., 0.1% or absolute 1e-6) for floating point inaccuracies
  if (abs(tss) > 1e-9 && abs(sum(ss_vec, na.rm=TRUE) - tss) / abs(tss) > 0.001 && abs(sum(ss_vec, na.rm=TRUE) - tss) > 1e-6) {
    warning(paste("Sum of SS across levels (", round(sum(ss_vec, na.rm=TRUE), 4),
                  ") does not closely match TSS (", round(tss, 4),
                  "). This might indicate issues with NA handling or calculations.", sep=""))
  }
  # Check if sum of df across levels equals TDF
  if (!is.na(sum(degf_vec, na.rm=TRUE)) && sum(degf_vec, na.rm=TRUE) != tdf) {
    warning(paste("Sum of df across levels (", sum(degf_vec, na.rm=TRUE),
                  ") does not match TDF (", tdf,
                  "). This might indicate issues with df calculation, especially if levels have few non-NA cells.", sep=""))
  }
  
  # --- Compute Mean Square (MS) per Level ---
  # MS = SS / df for each level
  message("Calculating Mean Squares...")
  ms_values <- rep(NA_real_, num_levels)
  # Avoid division by zero if df is 0 or NA
  valid_df_idx <- which(!is.na(degf_vec) & degf_vec > 0)
  if (length(valid_df_idx) > 0) {
    ms_values[valid_df_idx] <- ss_vec[valid_df_idx] / degf_vec[valid_df_idx]
  } else if (any(!is.na(degf_vec) & degf_vec <= 0)) {
    warning("Some levels have zero or negative degrees of freedom. Mean Square cannot be calculated for these levels.")
  }
  
  # --- Calculate Scales (Mean Resolution) ---
  # Calculate the representative scale (e.g., mean resolution) for each level
  scales <- sapply(1:num_levels, function(level) {
    mean(res(level_rasters[[level]]))
  })
  
  # --- Finalize SVC Table ---
  message("Calculating SS Proportions and Finalizing Table...")
  
  # Calculate percentage contribution of SS to TSS
  ss_p <- rep(NA_real_, num_levels)
  if (abs(tss) > 1e-9) { # Avoid division by zero if TSS is effectively zero
    ss_p <- ss_vec / tss
  } else if (all(abs(ss_vec) < 1e-9)) { # If all SS are zero and TSS is zero
    ss_p <- rep(0, num_levels)
  } else {
    warning("Total Sum of Squares (TSS) is near zero, cannot calculate proportions.")
  }
  
  # Ensure proportions sum approximately to 1 (or 0 if TSS was 0)
  if (abs(tss) > 1e-9 && abs(sum(ss_p, na.rm=TRUE) - 1.0) > 0.001) {
    warning("Sum of SS proportions (", round(sum(ss_p, na.rm=TRUE), 4), ") does not sum to 1. Check calculations.")
    # Optional: Normalize if desired, but warning is usually better
    # ss_p <- ss_p / sum(ss_p, na.rm = TRUE)
  }
  
  # Calculate cumulative percentage
  ss_cumulative_p <- cumsum(ifelse(is.na(ss_p), 0, ss_p)) # Treat NA as 0 for cumulative sum
  
  # Create the summary table
  svc <- tibble(
    level = 1:num_levels,
    scale = scales,             # Mean resolution at this level
    sum_squares = ss_vec,       # Sum of squares comparing level l to l+1
    degf = degf_vec,            # Degrees of freedom for SS[l]
    mean_square = ms_values,    # Mean Square (SS[l] / df[l])
    ss_p = ss_p,                # Proportion of TSS from SS[l]
    ss_cumulative_p = ss_cumulative_p # Cumulative proportion of TSS
  )
  
  # --- Compute Scale Variance Elements (SVE) Rasters (Optional) ---
  sve_rasters <- NULL
  if ("sve" %in% output_vars) {
    message("Calculating Scale Variance Elements (SVE) Rasters...")
    sve_list <- vector("list", num_levels)
    # Create a template raster with NAs where original had NAs
    rast_template_na <- rast_template
    values(rast_template_na) <- NA # Set all to NA initially
    
    for (level in 1:num_levels) {
      # Calculate squared difference for this level vs next level
      sq_diff_level <- (df_values[[paste0("value_level", level + 1)]] - df_values[[paste0("value_level", level)]])^2
      # Create a raster for this level's SVE
      sve_rast_level <- rast_template_na # Start with NA template
      # Fill in the values for the originally valid cells
      values(sve_rast_level)[valid_cell_idx] <- sq_diff_level
      sve_list[[level]] <- sve_rast_level
    }
    # Combine the list of rasters into a single multi-layer SpatRaster
    if (length(sve_list) > 0) {
      sve_rasters <- tryCatch({
        rast(sve_list)
      }, error = function(e) {
        warning("Could not combine SVE rasters: ", e$message)
        NULL # Return NULL if combination fails
      })
      if (!is.null(sve_rasters)) {
        names(sve_rasters) <- paste0("sve_level", 1:num_levels)
      }
    } else {
      sve_rasters <- NULL
    }
    message("SVE calculation complete.")
  }
  
  # --- Structure Output ---
  message("Finalizing results...")
  results <- list()
  if ("svc" %in% output_vars) results$svc <- svc
  if ("sve" %in% output_vars) results$sve <- sve_rasters
  if ("tss" %in% output_vars) results$tss <- tss
  if ("tdf" %in% output_vars) results$tdf <- tdf
  if ("level_rasters" %in% output_vars) results$level_rasters <- level_rasters
  if ("details" %in% output_vars) results$details <- df_values # Contains original cell values at each level
  
  message("Scale variance analysis finished.")
  return(results)
}
