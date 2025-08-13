from avatars import generate_player_headshot, pil_to_qpixmap

img = generate_player_headshot(
    player_name="Brian Pleasant",
    team_primary_hex="#00338D",
    team_secondary_hex="#C8102E",
    size=512
)
img.save("brian_pleasant.png")  # or use pil_to_qpixmap(img) inside PyQt6

# Tiny version for cards / UI lists
img_150 = img.resize((150, 150), resample=Image.LANCZOS)
img_150.save("brian_pleasant_150.png")
