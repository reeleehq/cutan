# The Umbrella

A stranger at a dusk bus stop, a missed last bus, and one umbrella between two people.

## Length and look

About 23 seconds, 1280x720 at 24 fps. No named style; a style pack of its own (`dusk`): a thin dark outline and a soft paper shadow on characters and props, and a light grain. Flat cut-out shapes, a dusk palette (indigo sky warming to orange at the horizon, slate buildings with lit windows), warm costume colours against it.

## Cast

| id | who | look | voice | moods |
|---|---|---|---|---|
| `mara` | waiting for a bus that has gone; dry, a little guarded | tall, long dark hair in a bun, plum coat, dark trousers | late 20s, low and dry, unhurried, understated | skeptical, sad, amused, happy |
| `teo` | a stranger who sees the bright side of everything | short and round, red cap, curly hair, mustard jacket | 30s, bright and quick, warm, a touch too loud | happy |

The two differ in build (tall and thin against short and round) and in colour (plum against mustard), so they read apart even in silhouette.

## Sets and props

- `bus_stop`: a dusk gradient sky, a skyline plate (my drawing), a grey pavement, and a bus shelter plate with a route-9 sign and a bench (my drawing). Characters stand in front of the shelter.
- `title_card`: a near-black card.
- `title`: the title text, revealed word by word.
- `umbrella`: a red umbrella (my drawing), held out by Teo in the last shot.

## Shot list

| shot | length | framing | camera | what happens |
|---|---|---|---|---|
| `title` | 3.0 s | card | hold | "The Umbrella" fades in word by word |
| `arrival` | 9.0 s | wide | hold | Teo walks in from the left in profile, turns to us, hops, greets Mara; she turns three-quarters toward him, skeptical |
| `regret` | 4.0 s | close single on Mara | push in | she admits the last bus left without her; a small nod |
| `offer` | 7.0 s | wide | hold | Teo holds out an umbrella; Mara hops, then smiles; the film fades out |

## Voices

`mara_voice` and `teo_voice` are expressive ElevenLabs voices (`eleven_v3`) with the padding trimmed; Teo's runs 8% faster. The voices themselves are to be cast from the notes in the cast table.

## Sound

Light rain throughout, a distant bus pulling away under `regret`, a soft pop when the umbrella appears. No music, or a sparse piano under the last shot. Nothing is included: these need licensed audio.

## Decisions I made

- Teo walks in profile (the walk reads best side-on) and turns to the front before speaking.
- The close-up mirrors Mara so she faces left, toward where Teo stands, and looks down.
- The umbrella is a separate prop placed at Teo's hand while his arm is raised; his arm stays up to the end of the shot so they stay together.
- Mara's last line is `amused` rather than `surprised`: factory eyes cannot open wider, and the dry delivery suits her.

## Open questions

- Voice casting for both characters (the `voice_id` of each voice document).
- Licence for the three drawings (skyline, shelter, umbrella): this example marks them CC0.

## Check

`python scripts/validate_pack.py examples/the-umbrella`: `PASS: 13/13 checks passed, 0 warning(s)`.
