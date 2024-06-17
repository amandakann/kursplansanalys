library(tidyverse)
library(ggpubr)
options(OutDec= ",")

datafil <- "representation_scb.csv"
titel <- "Över- och underrepresentation av verb per ämnesområde"

df <- read.csv(file.path("Visualiseringar", "data", datafil), sep=";")
df_t <- df %>%
    relocate(Hum, .before = SamJur) %>%
    pivot_longer(cols = 3:6, names_to = "område", values_to = "diff") %>%
    group_by(verb) %>%
    mutate(område = factor(område, unique(område)))

plot <- ggplot(df_t, aes(x=verb, y=diff, fill=område)) +
    geom_col(position="dodge", width=0.6) + 
    geom_hline(yintercept = 0, linetype="dashed", color = "black") +
    scale_y_continuous(breaks = seq(-0.6, 0.6, by = 0.15)) + 
    scale_x_discrete(position="top") +
    labs(
        title = titel,
        y = "Relativ skillnad mot snitt (för alla områden)",
        fill = "Ämnesområde: "
    ) + 
    theme_minimal() +
    scale_fill_manual(
    values = c(
        "#332288", 
        "#44AA99", 
        "#DDCC77", 
        "#CC6677")) +
    theme(
        legend.position = "bottom",
        plot.title = element_blank(),
        # plot.title = element_text(
        #     size = 20,
        #     face = "bold",
        #     hjust = 0.5
        # ),
        axis.title.x = element_blank(),
        axis.text.x = element_text(
            size = 20,
            face = "italic",
            hjust = 0.5
        ),
        axis.title.y = element_text(
            size = 18
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
ggsave(utdata, plot = plot, width = 40, height = 20, units = "cm")