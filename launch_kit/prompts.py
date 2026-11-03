"""Prompts shared with the Launch Kit web app (generated from its source)."""

STYLE_GUIDE_SYSTEM = "You are the art director of a game studio. Given a game name and pitch, you write a tight brand style guide that every downstream image, video and sound model will follow, so the whole storefront looks like ONE game.\nEverything must be ORIGINAL: never name, reference or imitate an existing game franchise, its logo, characters, factions or signature art; if the pitch names one, keep only the genre and mood.\nReturn ONLY a JSON object, no prose. It must be valid JSON: inside string values use single quotes, never unescaped double quotes. Match exactly:\n{\n  \"title\": string,                // the game's title, exact spelling as given\n  \"tagline\": string,              // <= 8 words\n  \"genre\": string,\n  \"mood\": string,                 // 3-5 adjectives\n  \"artStyle\": string,             // one dense style phrase reused in EVERY image prompt (medium, rendering, lighting, line quality, palette words)\n  \"palette\": [{\"name\": string, \"hex\": \"#RRGGBB\"}],  // exactly 5; [0] primary, [1] accent, [2] dark, [3] light, [4] highlight\n  \"fontVibe\": string,             // lettering direction for the title logo\n  \"logoPrompt\": string,           // for a text-rendering model: the title logo treatment ONLY. Must contain the exact title in quotes, centered, isolated on a flat solid plain white background, no scene, no other text\n  \"emblemPrompt\": string,         // a simple bold vector emblem/mark for the app icon. No text or letters. Centered, flat, iconic\n  \"keyArtPrompt\": string,         // cinematic wide key art of the game's hero moment. ABSOLUTELY NO TEXT, letters or logos. Leave calm negative space in the center-upper area for a logo\n  \"stingPrompt\": string,          // 5s camera motion + effects for an animated title reveal starting from the key art with logo (e.g. slow push-in, particles, light sweep, logo glints). Include the sound design in words\n  \"trailerPrompt\": string,        // a 12-second game trailer as 4 numbered shots (~3s each): 1) atmospheric establishing shot of the world, 2) the hero in action, 3) the core gameplay fantasy at its most exciting, 4) a final beat that resolves on the title logo. Describe camera moves, action and music/sound. Original characters only\n  \"trailerLine\": string,          // ONE short narrator line for the trailer, <= 10 words, punchy, no game title\n  \"icons\": [{\"name\": string, \"prompt\": string}],     // exactly 6 in-game UI/item icons that fit the game (e.g. health, currency, signature item, ability), each a single centered object\n  \"sfx\": [{\"name\": string, \"prompt\": string, \"seconds\": number}], // exactly 3: \"Title sting\" (3-5s), \"Menu select\" (0.5-1s), \"Level up\" (1.5-3s). Describe the sound concretely\n  \"storeBlurb\": string,           // 2-3 sentence Steam short description, punchy\n  \"features\": [string]            // exactly 4 store feature bullets, each <= 10 words\n}"

# Store aisles: the art direction each one adds to the style guide.
AISLES = {
    "Open-World Crime": {
        "id": "crime",
        "direction": "modern open-world crime epic: sun-drenched coastal metropolis, neon nightlife, sports cars and palm trees, bold graphic poster illustration with hard cel shading, hot sunset pink, teal and gold, heavy condensed italic slab lettering",
        "example_name": "Sunset Syndicate",
        "example_pitch": "An open-world crime saga where two siblings run getaway cars for a beachside crime family in a neon coastal city."
    },
    "Military Shooter": {
        "id": "shooter",
        "direction": "AAA military shooter: gritty cinematic photoreal key art, smoke, tracer fire and dust, desaturated steel greys with signal orange, sharp stencil-cut industrial lettering",
        "example_name": "Iron Front",
        "example_pitch": "A squad-based military shooter where an elite unit fights through a collapsing near-future megacity."
    },
    "Space Strategy": {
        "id": "rts",
        "direction": "sci-fi real-time strategy with original designs: sleek white-and-amber exo-suit colonists with hover tanks versus a crystalline glass-bodied alien swarm on a ringed desert moon, epic painterly concept art seen from a high strategic angle, teal and amber with magenta crystal glow, heavy beveled metallic lettering",
        "example_name": "Hive Dominion",
        "example_pitch": "A real-time space strategy game where human colonists, psionic aliens and a bug swarm fight over a dying star system."
    },
    "Block Sandbox": {
        "id": "sandbox",
        "direction": "voxel survival sandbox with its own look: soft rounded bevelled voxels like glossy toy bricks, pastel-bright candy greens, sky blue and coral, tiny chibi explorer characters with round helmets and backpacks (original designs, not blocky square-headed people), warm diorama lighting, chunky lettering built from rounded cubes",
        "example_name": "Blockhaven",
        "example_pitch": "A voxel survival sandbox where you dig, craft and build a floating island town before the void swallows it."
    },
    "Fantasy RPG": {
        "id": "rpg",
        "direction": "open-world fantasy RPG: frozen northern mountains, ancient stone ruins and a dragon on the horizon, cinematic oil-painting realism, cold steel blue and ember gold, carved weathered stone serif lettering",
        "example_name": "Frostbound",
        "example_pitch": "An open-world fantasy RPG where a dragon-blooded exile roams frozen northern kingdoms relearning forgotten rune magic."
    },
    "Retro Arcade": {
        "id": "arcade",
        "direction": "80s/90s arcade cabinet energy: crisp pixel art, CRT glow, neon magenta and cyan, chunky bitmap lettering",
        "example_name": "Neon Drift Undead",
        "example_pitch": "A synthwave racing roguelike where you outrun a zombie horde through a burning city at 300 km/h."
    },
    "Your Own": {
        "id": "own",
        "direction": "",
        "example_name": "",
        "example_pitch": ""
    }
}

LEGIBILITY_PROMPT = (
    "This is a game store capsule shown at its smallest real size (120x45 px, as in Steam search results). "
    'The game\'s title is "{title}". Can a shopper read the title at this size? '
    'Return ONLY JSON: {{"score": 1-10, "readable": boolean, "tip": "one short, concrete fix if needed"}}'
)
