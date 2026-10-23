# Run from the repository root:
# Rscript -e 'testthat::test_file("dsir-gho/tests/test_backend_comparison.R")'
library(testthat)
source(test_path("..", "evals", "compare_backends.R"))

# These are synthetic observations and synthetic review evidence, never WHO data.
synthetic_review <- function() {
  checks <- c("catalogues", "definition", "unit", "population", "estimate_type",
              "geography", "time", "dimensions", "release")
  list(approved = TRUE, reviewed_by = "Synthetic test reviewer",
       reviewed_at = "2026-10-22", legacy_code = "SYNTHETIC_L",
       xmart_code = "SYNTHETIC_X", key_fields = c("location", "year", "sex", "age"),
       checks = setNames(lapply(checks, function(x)
         list(status = "verified", evidence = paste("Synthetic evidence:", x))), checks))
}

synthetic_extract <- function(backend) {
  list(indicator_code = if (backend == "legacy") "SYNTHETIC_L" else "SYNTHETIC_X",
       data = data.frame(location = "PHL", year = 2020:2021,
                        sex = "total", age = "one_year",
                        value_num = c(80, 81), low = c(NA_real_, 79), high = c(NA_real_, 83)),
       provenance = list(backend = backend, complete = TRUE,
                         query_url = paste0("https://example.invalid/", backend),
                         retrieved_at = "2026-10-22T00:00:00Z"))
}

compare_synthetic <- function(legacy = synthetic_extract("legacy"),
                               xmart = synthetic_extract("xmart"), review = synthetic_review(), ...) {
  compare_backend_extracts(legacy, xmart, review,
                          key_fields = c("location", "year", "sex", "age"), ...)
}

test_that("every comparability check is required before comparing values", {
  for (field in names(synthetic_review()$checks)) {
    review <- synthetic_review()
    review$checks[[field]]$status <- "unverified"
    result <- compare_synthetic(review = review)
    expect_identical(result$status, "unverified")
    expect_false(result$values_compared)
    expect_null(result$differences)
  }
  review <- synthetic_review()
  review$approved <- FALSE
  expect_identical(compare_synthetic(review = review)$status, "unverified")
  review <- synthetic_review()
  review$checks$dimensions$evidence <- ""
  expect_identical(compare_synthetic(review = review)$status, "unverified")
})

test_that("independent values are matched by all reviewed keys, not row order", {
  xmart <- synthetic_extract("xmart")
  xmart$data <- xmart$data[2:1, ]
  expect_identical(compare_synthetic(xmart = xmart)$status, "equal")
  xmart$data$value_num[1] <- 70
  result <- compare_synthetic(xmart = xmart)
  expect_identical(result$status, "differences")
  expect_identical(result$differences$value_num$year, 2021L)
  expect_equal(result$differences$value_num$delta, -11)
})

test_that("coverage and strata differences remain explicit without filling", {
  xmart <- synthetic_extract("xmart")
  xmart$data$age[2] <- "two_years"
  result <- compare_synthetic(xmart = xmart)
  expect_identical(result$status, "differences")
  expect_length(result$differences, 0L)
  expect_equal(result$matched_rows, 1L)
  expect_equal(nrow(result$legacy_only), 1L)
  expect_equal(nrow(result$xmart_only), 1L)
  expect_equal(xmart$data$age[2], "two_years")
})

test_that("missing values, bounds and declared tolerances are compared separately", {
  xmart <- synthetic_extract("xmart")
  xmart$data$value_num[1] <- xmart$data$value_num[1] + 1e-11
  expect_identical(compare_synthetic(xmart = xmart)$status, "equal")
  xmart$data$low[1] <- 0
  result <- compare_synthetic(xmart = xmart)
  expect_true(is.na(result$differences$low$legacy))
  expect_equal(result$differences$low$xmart, 0)
  expect_true(is.na(result$differences$low$delta))
  expect_error(compare_synthetic(abs_tol = -1), "Tolerances")
})

test_that("duplicates, incomplete downloads and unknown keys cannot pass", {
  xmart <- synthetic_extract("xmart")
  xmart$data <- rbind(xmart$data, xmart$data[1, ])
  expect_identical(compare_synthetic(xmart = xmart)$status, "ambiguous_keys")
  for (field in c("backend", "complete", "query_url", "retrieved_at")) {
    xmart <- synthetic_extract("xmart")
    xmart$provenance[[field]] <- NULL
    result <- compare_synthetic(xmart = xmart)
    expect_identical(result$status, "incomplete")
    expect_false(result$values_compared)
  }
  xmart <- synthetic_extract("xmart")
  xmart$data$age[1] <- NA_character_
  expect_error(compare_synthetic(xmart = xmart), "Unknown key")
})

test_that("empty or disjoint data are not evidence of equal values", {
  xmart <- synthetic_extract("xmart")
  xmart$data <- xmart$data[0, ]
  expect_identical(compare_synthetic(xmart = xmart)$status, "no_overlap")
  xmart <- synthetic_extract("xmart")
  xmart$data$year <- 2030:2031
  expect_false(compare_synthetic(xmart = xmart)$values_compared)
})

test_that("reviewed source codes and complete dimension keys cannot be replaced", {
  xmart <- synthetic_extract("xmart")
  xmart$indicator_code <- "SAME_TITLE_DIFFERENT_MEASURE"
  expect_identical(compare_synthetic(xmart = xmart)$status, "unverified")
  review <- synthetic_review()
  review$key_fields <- c("location", "year")
  expect_error(compare_synthetic(review = review), "complete reviewed dimension mapping")
})
