# Fighter lobby and shared control modes

The game entry screen now shows the player's saved Quaternius fighter and exact muscle LV/EXP values from the same character growth data used by the profile. The right-hand panel includes all five body-part groups and individual arm levels. The bottom menu offers Training, Friends, disabled Bot, and Settings. Bot remains unavailable.

The original generated industrial-wall environment is a 271 KiB WebP with lighting baked into the image. It has no animated background or runtime environment geometry. The fighter preview renders on asset load and resize, with no continuous animation loop, and releases its GPU resources when entering the ring or leaving the page. The menu never starts the camera. Boxing suppresses the site's decorative click particles while other pages retain them.

Choosing Training or Friends opens a required Computer/Tracking selector. No option is preselected. The host's selection is stored in the room, shown with invitations, inherited by the accepting player and locked for that match. Server validation rejects invitations without a supported mode and conflicting mode overrides. Existing rooms without a mode field retain tracking behavior. Profile data, account ownership and rewards are preserved without migrations.

## Computer controls

| Action | Default |
| --- | --- |
| Move forward / left / back / right | W / A / S / D |
| Left / right punch | Q / E |
| Left / right front kick | U / I |
| Crouch | C |
| Dash with a movement direction | Space + WASD |
| Guard, hold three seconds | F |
| Slip left / right | Z / X |
| Lean back | R |

Settings changes the application language and saves unique keyboard bindings in this browser. Duplicate or reserved bindings are rejected, Escape cancels key capture, and Restore defaults resets the bindings. References display the current assignments. Movement uses the physical key position, including with a Thai keyboard layout.

Keyboard movement starts immediately, supports diagonals at normalized speed, automatically faces the opponent and drives footwork from actual displacement. Punches coordinate shoulder/hip rotation with arm extension. Front kicks lift the selected leg, retain the planted support foot, preserve bone lengths and constrain the foot against the bag/opponent capsules. Kick damage uses the saved legs level. A body kick can connect through a crouch; directional evasion and guard still apply. Tracking does not enable kicks or dashes.

A dash lasts 180 ms at 2.6× walking speed, with a 650 ms cooldown and a direction fixed for the burst. Holding Space cannot repeat dashes. The server enforces timing, normalizes diagonal speed, clamps the cage boundaries and sweeps relative movement to prevent opponents crossing through each other during simultaneous dashes. Existing knockdown, ten-second recovery, best-of-three and belt rules remain intact.

## Review and verification

- [Desktop lobby](lobby-desktop.png) / [Phone lobby](lobby-mobile.png)
- [Required control selection](control-selection.png)
- [Language and remappable keys](settings.png)
- [Male front kick](kick-male.png) / [Female front kick](kick-female.png)

Local tests use disposable accounts and databases. Browser coverage compares displayed levels with authenticated profile data, checks desktop/mobile layout, disabled Bot, explicit mode selection, camera-free keyboard play, inherited modes, remapping and language persistence, punches/kicks/crouch/dashes, remote state and cleanup. Rig tests measure both leg chains and foot contact with real saved avatar assets. The full tracking championship completes 2–1 with knockdown/recovery and one belt. Server tests cover mode validation, kick replay, dash duration/cooldown, cage bounds and simultaneous-dash collision. Node fixtures cover input edges, held-key suppression, blur cleanup and pose tracking.

Visual contact is a capsule approximation; authoritative hit resolution continues to use range, timing, direction, evasion and guard. This is original game behavior inspired by the supplied references, not an exact recreation of their physics or animations. Single-camera tracking accuracy still depends on visibility and the user's setup.
