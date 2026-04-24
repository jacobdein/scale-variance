library(terra)
library(tidyverse)
library(here)
library(sf)

set.seed(1)

# Create a sample raster with spatial pattern and NAs
r <- rast(nrows=64, ncols=64, xmin=0, xmax=64, ymin=0, ymax=64, crs="local")
xy <- xyFromCell(r, 1:ncell(r))
values(r) <- sin(xy[,1]/5) * cos(xy[,2]/5) * 100 + rnorm(ncell(r), 0, 20)
r[sample(ncell(r), 500)] <- NA # Add some NAs

plot(r, main="Original Raster Data")

# --- Example 1: Basic analysis with automatic levels ---
sv_results_auto <- compute_scale_variance_raster(r)
print("--- SVC Table (Auto Levels) ---")
print(sv_results_auto$svc)
print(paste("TSS:", round(sv_results_auto$tss, 2)))
print(paste("TDF:", sv_results_auto$tdf))

# Plot the results based on SS percentages
if (!is.null(sv_results_auto$svc) && nrow(sv_results_auto$svc) > 0) {
  plot(sv_results_auto$svc$scale, sv_results_auto$svc$ss_p,
       type='b', log='x', pch=16, ylim=c(0, max(sv_results_auto$svc$ss_p, na.rm=TRUE)*1.1),
       xlab="Scale (Mean Resolution)", ylab="Proportion of Total Sum of Squares",
       main="Scale Variance Analysis (based on SS)")
  lines(sv_results_auto$svc$scale, sv_results_auto$svc$ss_cumulative_p, type='b', pch=1, col='blue')
  abline(h=0, lty=2, col='grey')
  legend("topleft", legend=c("SS Proportion (%)", "Cumulative SS Proportion (%)"),
         pch=c(16, 1), col=c("black", "blue"), lty=1, bty="n")
}

# --- Example 2: Specify levels and request SVE ---
sv_results_sve <- compute_scale_variance_raster(r, num_levels = 4,
                                               output_vars = c("svc", "sve", "tss"))
print("--- SVC Table (4 Levels) ---")
print(sv_results_sve$svc)

if (!is.null(sv_results_sve$sve)) {
  plot(sv_results_sve$sve, main="Scale Variance Elements (Squared Differences)")
}

# --- Example 3: Using 'sum' aggregation ---
sv_results_sum <- compute_scale_variance_raster(r, agg_fun = "sum")
print("--- SVC Table (Aggregation: sum) ---")
print(sv_results_sum$svc)

# --- Example 4: Using Fig3 from Moellering and Tobler 1972 ---
# Create a dummy CSV file for the example if it doesn't exist
fig3_csv_path <- here("../../part 1/notebooks/Fig3.csv")
if (!file.exists(fig3_csv_path)) {
  fig3_mat_data <- matrix(c(
    2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
    5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
    2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
    5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
    2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
    5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
    2, 5, 2, 5, 2, 5, 2, 5, 5, 8, 5, 8, 5, 8, 5, 8,
    5, 2, 5, 2, 5, 2, 5, 2, 8, 5, 8, 5, 8, 5, 8, 5,
    5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
    8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
    5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
    8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
    5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
    8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2,
    5, 8, 5, 8, 5, 8, 5, 8, 2, 5, 2, 5, 2, 5, 2, 5,
    8, 5, 8, 5, 8, 5, 8, 5, 5, 2, 5, 2, 5, 2, 5, 2
  ), nrow = 16, ncol = 16, byrow = TRUE)
  write.table(fig3_mat_data, fig3_csv_path, sep = ",", row.names = FALSE, col.names = FALSE)
  message("Created dummy Fig3_MT1972.csv for example 4.")
}

# Check if the file exists before reading
if (file.exists(fig3_csv_path)) {
  fig3_matrix <- as.matrix(read_csv(fig3_csv_path, col_names = FALSE, col_types = cols(.default = col_double())))
  fig3_raster <- rast(fig3_matrix)
  # Set extent for scale calculation (assuming unit cells)
  ext(fig3_raster) <- c(0, ncol(fig3_raster), 0, nrow(fig3_raster))
  crs(fig3_raster) <- "local" # Assign a CRS

  fig3_sv_results <- compute_scale_variance_raster(fig3_raster, output_vars = c("svc", "tss", "tdf"))
  print("--- SVC Table (Moellering & Tobler 1972 Fig 3 Data) ---")
  print(fig3_sv_results$svc)
  print(paste("TSS:", fig3_sv_results$tss)) # Should be 1152
  print(paste("TDF:", fig3_sv_results$tdf)) # Should be 255

  # Plot results for Example 4
  if (!is.null(fig3_sv_results$svc) && nrow(fig3_sv_results$svc) > 0) {
     plot(fig3_sv_results$svc$scale, fig3_sv_results$svc$ss_p,
          type='b', log='x', pch=16, ylim=c(0, max(fig3_sv_results$svc$ss_p, na.rm=TRUE)*1.1),
          xlab="Scale (Mean Resolution)", ylab="Proportion of Total Sum of Squares",
          main="Scale Variance Analysis (M&T Fig 3 - based on SS)")
     lines(fig3_sv_results$svc$scale, fig3_sv_results$svc$ss_cumulative_p, type='b', pch=1, col='blue')
     abline(h=0, lty=2, col='grey')
     legend("topleft", legend=c("SS Proportion (%)", "Cumulative SS Proportion (%)"),
            pch=c(16, 1), col=c("black", "blue"), lty=1, bty="n")
  }

} else {
  warning("Could not find ", fig3_csv_path, " to run Example 4.")
}


# --- Example 4: Using Fig3 from Moellering and Tober 1972  ---
fig3_matrix <- as.matrix(read_csv(here("../../part 1/notebooks/Fig3.csv"), col_names = FALSE, col_types = cols(.default = col_double())))
fig3_raster <- rast(fig3_matrix)
fig3_sv_results <- compute_scale_variance_raster(fig3_raster, output_vars = c("svc", "sve", "tss"))
print(fig3_sv_results$svc)

plot(fig3_sv_results$sve)

# --- Example 5: Using NDVI from greater London ---
source("./scale variance.R")

ndvi_filepath <- here("../../part 2/data/NDVI/NDVI_10m.tif")
ndvi_raster <- rast(ndvi_filepath)

aoi <- read_sf(here("../../part 2/data/AOI.geojson")) %>% 
  st_transform(crs = st_crs(ndvi_raster))

# clip ndvi_raster to aoi
ndvi_raster <- terra::crop(ndvi_raster, aoi)
plot(ndvi_raster)

# resample 10-meter raster (6400 x 6400 cells) to a resolution of 15.625m and keep same square extent (64km x 64km)
template_raster <- rast(extent = ext(ndvi_raster), 
                        resolution = 15.625, 
                        crs = crs(ndvi_raster))
ndvi_raster_re <- terra::resample(x = ndvi_raster, 
                          y = template_raster, 
                          method = "bilinear")
plot(ndvi_raster_re)
print(ndvi_raster)
print(ndvi_raster_re)

ndvi_sv_results <- compute_scale_variance_raster(ndvi_raster, output_vars = c("svc", "sve", "tss"))
print(ndvi_sv_results$svc)
plot(ndvi_sv_results$sve)

# plot svc
ndvi_sv_results$svc %>% 
  ggplot(aes(x = scale, y = ss_p)) +
  geom_line() +
  geom_point() +
  # log scale x
  scale_x_log10()


ndvi_re_sv_results <- compute_scale_variance_raster(ndvi_raster_re, output_vars = c("svc", "sve", "tss"))
print(ndvi_re_sv_results$svc)
plot(ndvi_re_sv_results$sve)

# plot svc
ndvi_re_sv_results$svc %>% 
  ggplot(aes(x = scale, y = ss_p)) +
  geom_line() +
  geom_point() +
  # log scale x
  scale_x_log10()
