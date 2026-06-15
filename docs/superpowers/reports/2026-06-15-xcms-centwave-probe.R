user_lib <- Sys.getenv("R_LIBS_USER")
if (nzchar(user_lib)) {
  .libPaths(user_lib)
}

suppressPackageStartupMessages({
  library(xcms)
  library(MSnbase)
  library(BiocParallel)
})

files <- c(
  "C:/Xcalibur/data/20241025_CSMU_NA/200ugCTDNA_100uMCP_1.mzML",
  "C:/Xcalibur/data/20241025_CSMU_NA/50ugCTDNA_Control_1.mzML"
)

missing_files <- files[!file.exists(files)]
if (length(missing_files)) {
  stop("Missing input files: ", paste(missing_files, collapse = ", "))
}

sample_data <- data.frame(
  sample_name = basename(files),
  sample_group = c("probe", "probe")
)

raw <- readMSData(
  files,
  pdata = new("AnnotatedDataFrame", sample_data),
  mode = "onDisk"
)
raw <- filterRt(raw, c(0, 600))

param <- CentWaveParam(
  ppm = 10,
  peakwidth = c(5, 60),
  prefilter = c(3, 10000),
  noise = 10000
)

xdata <- findChromPeaks(raw, param = param, BPPARAM = SerialParam())
peaks <- as.data.frame(chromPeaks(xdata))

out_dir <- file.path("output", "mature_tools", "xcms_probe")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
out_file <- file.path(out_dir, "xcms_centwave_2sample_peaks.csv")
write.csv(peaks, out_file, row.names = FALSE)

cat("xcms_version", as.character(packageVersion("xcms")), "\n")
cat("input_files", length(files), "\n")
cat("rt_filter_seconds", "0-600", "\n")
cat("peak_rows", nrow(peaks), "\n")
cat("columns", paste(names(peaks), collapse = "|"), "\n")
cat("output", normalizePath(out_file), "\n")
