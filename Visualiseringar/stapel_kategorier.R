library(ggpubr)
library(tidyverse)
library(grafify)

datafil <- "kurser_nivå.csv"
gruppnamn <- "Lärosäte"
# färgskala <- scale_fill_manual(
#     values = c(
#         "#332288", 
#         "#44AA99", 
#         "#DDCC77", 
#         "#CC6677",
#         "gray"))
# färgskala <- scale_fill_brewer(palette = "YlOrRd")
# färgskala <- scale_fill_grafify(palette = "fishy")
färgskala <- scale_fill_brewer(palette = "YlGnBu")

df <- read.csv(file.path("Visualiseringar", "data", datafil), sep=";") %>%
    mutate(Grupp = factor(Grupp, unique(Grupp)))


plot <- ggplot(df, aes(x="", y = Courses, fill = Grupp)) +
    geom_bar(position="fill", stat="identity") +
    labs(
        title = paste("Andel kurser i korpusen\nper",tolower(gruppnamn)),
        fill = gruppnamn
    ) +
    scale_y_continuous(breaks = seq(0, 1, by = 0.2), labels=scales::percent) + 
    theme_minimal() +
#    coord_flip() +
    färgskala +
    theme(
        plot.title = element_text(
            size = 20,
            face = "bold",
            hjust = 0.5
        ),
        axis.title.x = element_blank(),
        axis.title.y = element_blank(),
        axis.text.x = element_text(
            size = 15
        ),
        axis.text.y = element_text(
            size = 15
        ),
        legend.title = element_text(
            size = 16
        ),
        legend.text = element_text(
            size = 14
        )
    )


utdata <- file.path("Visualiseringar", "figurer", paste(substring(datafil, 1, nchar(datafil) - 4), ".png", sep=""))
#ggsave(utdata, plot = plot, width = 20, height = 8, units = "cm")
ggsave(utdata, plot = plot, width = 15, height = 15, units = "cm")


plot <- ggplot(df, aes(x = Grupp, y = GpC, fill = Grupp)) +
    geom_bar(stat="identity") +
    labs(
        title = "Genomsnittligt antal mål per kurs",
    ) +
    scale_y_continuous(breaks = seq(0, 10, by = 2)) + 
    theme_minimal() +
    färgskala +
    theme(
        plot.title = element_text(
            size = 20,
            face = "bold",
            hjust = 0.5
        ),
        axis.title.x = element_blank(),
        axis.text.x = element_blank(),
        axis.title.y = element_blank(),
        axis.text.y = element_text(
            size = 15
        ),
        legend.position = "none"
    )

utdata <- file.path("Visualiseringar", "figurer", paste(substring(datafil, 1, nchar(datafil) - 4), "_mål.png", sep=""))
ggsave(utdata, plot = plot, width = 15, height = 10, units = "cm")