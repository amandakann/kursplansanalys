library(ggpubr)
library(tidyverse)

datafil <- "maxminbloom.csv"

df <- read.csv(file.path("Visualiseringar", "data", datafil), sep=",")

plot <- ggplot(df, aes(x=nivå, y=min)) +
    geom_bar(stat="identity", fill=c(
            "#a283c4", 
            "#7b9de6", 
            "#99deec", 
            "#93d981", 
            "#f8e26e", 
            "#f68e70")
            ) +
    geom_text(aes(label=min), vjust=-0.5, size=3.5) +
    ylim(0,7000) + 
    labs(
        title="Lägsta Bloomnivå per kurs",
        x="Bloomnivå",
        y="Antal kurser"
        ) +
    theme_minimal() +
    theme(
        plot.title = element_text(
            face = "bold",
            size = "20",
            hjust = 0.5),
        plot.caption = element_text(
            face = "italic",
            size = "18",
            hjust = 0.5
            ),
        axis.title = element_text(
            size = "15"
            ),
        axis.text = element_text(
            size = "12"
            ),
        plot.margin = unit(c(1,1,1,1), 'lines')) +
    scale_x_continuous("Bloomnivå", breaks=seq(0,6,1))

ggsave(file.path("Visualiseringar", "figurer", "minbloom.png"), plot = plot, width = 15, height = 12, units = "cm")

plot <- ggplot(df, aes(x=nivå, y=max)) +
    geom_bar(stat="identity", fill=c(
            "#a283c4", 
            "#7b9de6", 
            "#99deec", 
            "#93d981", 
            "#f8e26e", 
            "#f68e70")
            ) +
    geom_text(aes(label=max), vjust=-0.5, size=3.5) +
    ylim(0,7000) +
    labs(
        title="Högsta Bloomnivå per kurs",
        x="Bloomnivå",
        y="Antal kurser"
        ) +
    theme_minimal() +
    theme(
        plot.title = element_text(
            face = "bold",
            size = "20",
            hjust = 0.5),
        plot.caption = element_text(
            face = "italic",
            size = "18",
            hjust = 0.5
            ),
        axis.title = element_text(
            size = "15"
            ),
        axis.text = element_text(
            size = "12"
            ),
        plot.margin = unit(c(1,1,1,1), 'lines')) +
    scale_x_continuous("Bloomnivå", breaks=seq(0,6,1))

ggsave(file.path("Visualiseringar", "figurer", "maxbloom.png"), plot = plot, width = 15, height = 12, units = "cm")