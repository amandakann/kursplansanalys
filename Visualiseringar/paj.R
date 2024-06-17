library(ggplot2)
library(ggpubr)
library(tidyverse)
library(waffle)

df <- read.csv("Visualiseringar/verbperkurs.csv")

plot <- ggplot(df, aes(x = "", y = Count, fill = Range)) +
    geom_bar(width = 1, stat = "identity") +
    coord_polar("y", start = 0) +
    theme_void() +
    theme(legend.position = "none") +
    geom_text(aes(label = paste0(Range, " verb: \n", Count)), position = position_stack(vjust = 0.5)) +
    scale_fill_brewer(palette = "Pastel1") +
    labs(fill = "Antal aktiva verb\n per kurs", x = NULL, y = NULL) + 
    ggtitle("Antal aktiva verb per kurs") + 
    theme(
        plot.title = element_text(
            face = "bold",
            size = "20",
            hjust = 0.5),
    )

ggsave("Visualiseringar/verbperkurs.png", plot = plot, width = 12, height = 12, units = "cm")