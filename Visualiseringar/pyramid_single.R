library(tidyverse)
library(ggpubr)
options(OutDec= ",")

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
print(plot)