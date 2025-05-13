library(tidyverse)
library(ggpubr)
options(OutDec= ",")

datafil <- "verbpernivå_alla.csv"
titel <- "Andel verb per Bloomnivå"
format <- "ruta"

if (format == "platt") {
    col <- 4
    row <- 1
    w <- 40
    h <- 15
    s_title <- 25
    s_subtitle <- 20
    s_caption <- 18
    h_caption <- 0.98
    v_caption <- 12
    s_label <- 7
    s_annot <- 7
} else if (format == "ruta") {
    col <- 2
    row <- 2
    w <- 40
    h <- 30
    s_title <- 35
    s_subtitle <- 30
    s_caption <- 26
    s_label <- 10
    h_caption <- 0.9
    v_caption <- 8
    s_annot <- 10
}


df <- read.csv(file.path("data_2025_mar", datafil), sep=";")
df_t <- df %>%
    pivot_longer(cols = 2:7, names_to = "level", values_to = "counts") %>%
    group_by(Grupp) %>%
    mutate(perc=counts/sum(counts)) %>%
    mutate(perc.h = perc/2) %>%
    mutate(perc.h.n = -perc.h)
df_split <- split(df_t, factor(df_t$Grupp, unique(df_t$Grupp)))

plots = list()
for (i in names(df_split)) {
    plot <- ggplot(df_split[[i]], 
    aes(
        y = row.names(df_split[[i]]), 
        fill=row.names(df_split[[i]])
        )) +
    xlim(-0.18, 0.18) + 
    geom_bar(aes(x = perc.h), stat = "identity") +
    geom_bar(aes(x = perc.h.n), stat = "identity") +
    geom_hline(yintercept = df$Snitt[df$Grupp==i]+0.5, color = "gray", size = 1, linetype="dashed") +
    annotate("text", x = 0.14, y = df$Snitt[df$Grupp==i]+0.65, label = df$Snitt[df$Grupp==i], vjust = 0, hjust = 0, size = s_annot) +
    geom_text(aes(
        x = 0, 
        label = scales::percent(round(perc, 3), decimal.mark = ",", accuracy = 0.1)), 
        size = s_label
        ) +
    labs(
        title=i,
        caption=paste("Snittnivå",df$Snitt[df$Grupp==i])
        ) +
    theme_void() +
    scale_fill_manual(
        values = c(
            "#a283c4", 
            "#7b9de6", 
            "#99deec", 
            "#93d981", 
            "#f8e26e", 
            "#f68e70")
            ) +
    theme(
        legend.position = "none", 
        plot.title = element_text(
            face = "bold",
            size = s_subtitle,
            hjust = 0.5),
        plot.caption=element_blank(),
        # plot.caption = element_text(
        #     face = "italic",
        #     size = s_caption,
        #     hjust = h_caption,
        #     vjust = v_caption
        #     ),
        plot.margin = unit(c(2,0,0,0), 'lines'))
    plots <- append(plots, list(plot))
}


gridplot <- ggarrange(plotlist = plots, ncol = col, nrow = row) + 
    ggtitle(titel) +
    theme(
        plot.title = element_text(
            face = "bold",
            size = s_title,
            hjust = 0.5)
    )

#utdata <- file.path("figurer_2025_mar", paste(substring(datafil, 1, nchar(datafil) - 4), ".png", sep=""))
#ggsave(utdata, plot = gridplot, width = w, height = h, units = "cm")
