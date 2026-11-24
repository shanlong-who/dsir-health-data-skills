scope <- readLines("config/ghe-scope.txt", warn = FALSE)
stopifnot(length(scope) == 1L, scope %in% c("philippines", "regional"))
pilot <- scope == "philippines"
snapshot.id <- if (pilot) "phl-ghe-deaths" else "wpr-ghe-deaths"
out <- file.path("snapshots", snapshot.id)
catalog.dir <- "snapshots/phase5"
roster <- read.csv("config/wpr-areas.csv", colClasses = "character")
stopifnot(nrow(roster) == 38L, !anyNA(roster), !anyDuplicated(roster$area_code))
if (pilot) roster <- subset(roster, area_code == "PHL")
sex.codes <- c("FEMALE", "MALE", "TOTAL")
key <- c("area_code", "year", "sex", "age", "cause_code", "measure")
product <- "WHO Global Health Estimates"
endpoint <- "https://xmart-api-public.who.int/DEX_CMS/GHE_FULL"
raw.base <- "https://raw.githubusercontent.com/shanlong-who/dsir-health-data-skills/"
indicator <- list(code = "GHE/0/deaths", name = "All-cause deaths by sex", unit = "deaths",
                  cause_code = "0", cause_name = "All Causes", measure = "deaths",
                  age = "TOTAL", sex = sex.codes, product = product, backend = "xmart")
write_metadata <- function(object, path) {
  jsonlite::write_json(object, path, auto_unbox = TRUE, pretty = TRUE, null = "null",
                       na = "null", digits = NA)
}
validate_rows <- function(d) {
  stopifnot(nrow(d) > 0L, !anyNA(d[key]), !anyDuplicated(d[key]),
            all(d$area_code %in% roster$area_code), all(d$year == as.integer(d$year)),
            all(d$sex %in% sex.codes), all(d$age == "TOTAL"), all(d$cause_code == "0"),
            all(d$cause_name == "All Causes"), all(d$measure == "deaths"), all(d$unit == "deaths"))
  for (field in c("value", "low", "high")) {
    x <- d[[field]]
    stopifnot(all(is.na(x) | (is.finite(x) & x >= 0)))
  }
  stopifnot(all(d$low <= d$value, na.rm = TRUE), all(d$value <= d$high, na.rm = TRUE),
            all(d$low <= d$high, na.rm = TRUE))
  if (pilot) stopifnot(nrow(d) == 3L, all(d$year == 2023L), setequal(d$sex, sex.codes),
                       all(complete.cases(d[c("value", "low", "high")])))
}
