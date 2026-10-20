# Voices and a custom look (optional elements)

Both are optional. Without voice documents the film renders with silent, correctly timed placeholder speech; without a style pack it renders in the art's own colours.

## Voices: `assets/voices/<key>.json`

A voice document says who speaks a character's lines and how. Bind it to the character in `cast.sh` with `--voice-ref <key>` (`an character new mara --offline ... --voice-ref mara_voice`). Lines whose speaker is not a character in the shot (a narrator, someone off screen) use the voice named **`default`**: write `assets/voices/default.json` for a narrator.

```json
{
  "provider": "elevenlabs",
  "model_id": "eleven_v3",
  "voice_settings": {"stability": 0.5},
  "effects": {"trim_silence": true, "tempo": 1.08},
  "notes": "A man in his 50s from rural County Limerick: a soft, rounded Munster lilt, mid-low and warm, unhurried and chatty. Not stage-Irish and not Dublin."
}
```

| key | values |
|---|---|
| `provider` | `elevenlabs` (real, acted speech, billed per character: with this provider a plain render calls ElevenLabs; the pipeline owner previews silently with `an render --tts offline`) |
| `voice_id` | the provider's id for a particular voice. **Leave it out** unless the writer gives you one, or until the writer has chosen one in the voice-design round (`SKILL.md`): the chosen option's `voice_id` goes here. Without it, the document's key would be sent as the voice, so list it under open questions until it is chosen |
| `model_id` | `eleven_v3` (expressive: performs `[emotion]` and `{cues}` as acting; the right choice for drama and comedy), `eleven_multilingual_v2` (steady narration), `eleven_v4`, `eleven_v4_turbo`, `eleven_v3_conversational`; unset is a fast, flat model |
| `voice_settings` | `stability`: 0 to 1, lower is more emotional range (`eleven_v3` reads only 0.0 "creative", 0.5 "natural", 1.0 "robust"); `similarity_boost` 0 to 1; `style` 0 to 1 (`eleven_multilingual_v2` only); `use_speaker_boost` true/false; `speed` 0.7 to 1.2 (ignored by `eleven_v3`: use `tempo`) |
| `effects` | `pitch_semitones`: -12 to 12 (a higher, cartoonish voice: 3 to 5); `tempo`: 0.5 to 2 (1.1 is 10% faster, pitch kept); `trim_silence`: `true` cuts the breath and room tone a voice pads each line with (put it in every `elevenlabs` voice whose lines must start on the word), or `{"threshold_db": -45}` to cut only dead air and keep breaths |
| `notes` | the voice in words, 20 to 1000 characters: age, gender, accent (as local as the writer can say it: "rural County Limerick", not "Irish"), pitch, pace, texture, attitude, and what it must NOT sound like. Voices are designed from this text, so write it for the ear. The engine ignores it when it speaks |
| `sample_text` | optional: 100 to 1000 characters the designed samples say, ideally the character's own lines (left out, the pipeline uses the character's lines in the scene) |
| `loudness_offset_db` | keep this voice that many dB above the others (a narrator: 2) when the meta levels voices (`voice_loudness: -16`) |

The validator refuses any other key and any value out of range; an unknown `model_id` is a warning. With `eleven_v3`, a dialogue line's `[emotion]` and `{cues}` (`{whispers}`, `{sighs}`, `{deadpan}`, `{laughs}`) are performed; captions and lip-sync see only the words.

Put each character's voice in words in its document's `notes`, and the same words in `PRODUCTION.md`'s cast table: voices are designed from the notes, and the writer chooses among the samples.

## A custom look: `assets/styles/<name>.json`

A style pack recolours and finishes the whole film. Name it in the meta block: `style_pack: <name>`. A named style (South Park and the others) brings its own: copy it from `styles.md`. For a look of your own:

```json
{
  "kind": "StylePack",
  "name": "dusk",
  "roles": {"sky": "#1b2140", "ground": "#4a4f57"},
  "surface": {
    "outline": {"width": 2.0, "color": "#1d1a24"},
    "shadow": {"dx": 3.0, "dy": 3.0, "color": "#000000", "alpha": 0.25}
  },
  "grain": {"amount": 0.04}
}
```

| key | meaning |
|---|---|
| `roles` | colour by role, `#rrggbb`: `skin`, `hair`, `clothing`, `leg`, `accessory`, `pupil` recolour **every** factory character (so leave them out when each character has its own palette in `cast.sh`); `sky`, `ground` recolour the built-in environments; `stroke` colours path props that set no colour. Never `lip`, `mouth_fill`, `teeth`, `tongue`, `eye_sclera` (refused) |
| `entities` | per character: `{"mara": {"clothing": "#7a3b69"}}` overrides roles for one |
| `surface` | finishes on every character and prop: `outline` (`width` in the art's pixels, `color`), `shadow` (`dx`, `dy`, `color`, `alpha`: a paper-cut shadow), `glow` (`color`, `radius`, `intensity`) |
| `entity_surfaces` | per entity id, overriding `surface` key by key: `{"umbrella": {"glow": {"color": "#ffd27a", "radius": 12, "intensity": 0.8}}}`, or `{"mara": {"outline": false}}` to remove one |
| `grain` | a static paper texture over the frame: `amount` 0.02 to 0.1 (it only darkens), optional `seed`, `tile` |

Drawings you made keep their colours (roles reach only factory characters and built-in sets); outlines, shadows and grain reach everything. A character with an outline or shadow darkens while it fades (`alpha` below 1): for a long fade, switch its finish off with `entity_surfaces`.

## Sound and music

Not an element you can write: sound files need licensed audio. Describe the music and effects you want in `PRODUCTION.md` (what, where, how loud); the pipeline owner adds them.
