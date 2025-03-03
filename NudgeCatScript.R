library(readxl)
library(writexl)

FOIs <- list.files("C:/Users/tpd10/Gits/bwh-pharmacoepi-roybal/NudgeDataDownload",full.names = TRUE)

xlcat <- function(x) {x %>% 
  excel_sheets() %>% 
  set_names() %>% 
  map(read_excel, path = x) %>%
  map(clean_names)}

omnicel <- lapply(FOIs, xlcat) |> unlist(recursive = FALSE) |> reduce(full_join)

write_xlsx(omnicel, "C:/Users/tpd10/Gits/bwh-pharmacoepi-roybal/NudgeDataDownload/Nudge_Concatenated.xlsx")