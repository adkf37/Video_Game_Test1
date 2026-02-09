# Custom Hero Portraits

Place custom hero portrait images in this folder to replace the procedural bunnies.

## How to Add Custom Art

1. **File naming:** Name your PNG files exactly matching the hero ID from `data/heroes.json`
   - Example: For the "knight" hero → `knight.png`
   - For the "archer" hero → `archer.png`

2. **Image specs:**
   - **Format:** PNG (supports transparency)
   - **Recommended size:** 600x400 pixels (landscape orientation)
   - **Aspect ratio:** 3:2 works best (e.g., 600x400, 900x600, 1200x800)
   - **Style:** Any art style! Anime bunnies, pixel art, realistic, cartoons, etc.

3. **Fallback:** If no custom image is found, the game uses the default procedural bunny

## Example Hero IDs

Check `data/heroes.json` for the exact IDs. Your current heroes:
- `hero_1.png` - Fluffy the Savior
- `hero_2.png` - Rabbiticus the III
- `hero_3.png` - Hero 3 (The Wise)
- `hero_4.png` - Hero 4 (The Fierce)

## Tips

- **Transparency:** Use transparent backgrounds for clean portraits
- **Aspect ratio:** Square images work best (1:1 ratio)
- **File size:** Keep under 1MB for fast loading
- **Color:** Hero's color tint will be used for UI elements, not the portrait

## Testing Your Art

1. Add your PNG file to this folder
2. Run the game
3. Open Hero Management (H key)
4. Navigate to your hero to see the custom portrait with bounce animation!

If the image doesn't load, check:
- File name exactly matches hero ID (case-sensitive)
- File is actually PNG format
- File isn't corrupted

Have fun customizing your bunnies! 🐰🎨
