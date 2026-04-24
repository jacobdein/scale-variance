# Main script
library(terra)
library(tidyverse)
library(sf)

set.seed(1)

source("./scale variance/scale variance.R")

# Load NDVI data
ndvi_filepath <- "../data/NDVI/NDVI_Max_2023-0000000000-0000000000.tif"
ndvi_raster <- rast(ndvi_filepath)

#aoi <- read_sf("../data/AOI.geojson") %>% 
#  st_transform(crs = st_crs(ndvi_raster))

data_extent <- read_sf("../data/data_extent.geojson") %>% 
  st_transform(crs = st_crs(ndvi_raster))

aoi <- data_extent

boundary <- read_sf("../data/Greater London.geojson") %>% 
  st_transform(crs = st_crs(ndvi_raster))

# Clip NDVI raster to AOI
ndvi_raster <- terra::crop(ndvi_raster, aoi)

# Resample to 15.625m resolution
template_raster <- rast(extent = ext(ndvi_raster), 
                        #resolution = 15.625, 
                        resolution = 125, 
                        crs = crs(ndvi_raster))
ndvi_raster_re <- terra::resample(x = ndvi_raster, 
                                  y = template_raster, 
                                  method = "bilinear")

# Compute scale variance for NDVI
ndvi_sv_results <- compute_scale_variance_raster(ndvi_raster_re, 
                                                 output_vars = c("svc", "sve", "tss"))

# Load Land Cover data
lc_filepath <- "../data/Land Cover/Land_cover_10m.tif"
lc_raster <- rast(lc_filepath)

# Clip land cover raster to AOI
lc_raster <- terra::crop(lc_raster, aoi)

# Resample to 15.625m resolution
lc_raster_re <- terra::resample(x = lc_raster, 
                                y = template_raster, 
                                method = "near")

# Define land cover classes
lc_classes <- list(
  list(num = 4, name = "ca_Wa"),
  list(num = 6, name = "ca_Ur"),     # Position 2 in grid
  list(num = 5, name = "ca_Su"),  # Position 3 in grid
  list(num = 1, name = "ca_Wo"),     # Position 4 in grid
  list(num = 2, name = "ca_Ve"),      # Position 5 in grid
  list(num = 3, name = "ca_Ar")     # Position 6 in grid
)

# Create a list to store all factor data
all_factors <- list()

# Add NDVI factor (position 1 in grid)
all_factors[[1]] <- list(
  name = "NDVI",
  sv_results = ndvi_sv_results,
  raster = ndvi_raster_re
)

# Process each land cover class
for (i in 1:length(lc_classes)) {
  lc_class <- lc_classes[[i]]
  class_num <- lc_class$num
  class_name <- lc_class$name
  
  # Create binary raster for this class
  class_raster <- lc_raster_re
  class_raster[class_raster != class_num] <- 0
  class_raster[class_raster == class_num] <- 1
  
  # Compute scale variance
  class_sv_results <- compute_scale_variance_raster(class_raster, 
                                                    output_vars = c("svc", "sve", "tss"))
  
  # Add to factors list
  all_factors[[i + 1]] <- list(
    name = class_name,
    sv_results = class_sv_results,
    raster = class_raster
  )
}

# Create summary of scale variance for each factor accross all scales
sv_summary <- do.call(rbind, lapply(all_factors, function(factor) {
  data.frame(
    factor = rep(factor$name, 11),
    level = factor$sv_results$svc$level,
    scale = factor$sv_results$svc$scale,
    variance = factor$sv_results$svc$ss_p
  )
}))

# Save summary
write.csv(sv_summary, 
          file = "../data/env_factor_sv_extent.csv", 
          row.names = FALSE)

# plot variance by scale faceted by factor
ggplot(sv_summary, aes(x = scale, y = variance, color = factor)) +
  geom_line() +
  geom_point() +
  scale_x_log10() +
  facet_wrap(~ factor, scales = "free_y") +
  labs(title = "Scale Variance of Environmental Factors",
       x = "Scale (m)",
       y = "Variance") +
  theme_minimal() +
  theme(legend.position = "bottom")

