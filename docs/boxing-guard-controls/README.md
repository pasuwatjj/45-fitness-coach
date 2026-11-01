# Directional guard, controls, camera and bag-training lobby

Computer defaults are now Ctrl + WASD for a ducking dash, Space + A/D for left/right hooks, and Space + W for a right uppercut. The directional chord consumes walking input and needs a fresh key press for each strike. Holding F + Q/E selects left/right guard without punching; F alone or F + Q + E guards with both arms. Existing punch, kick, crouch and slip controls remain. Settings accept Ctrl and persist version-2 bindings; version-1 users migrate from Space dash while retaining compatible custom bindings. Ctrl shortcuts reserved by the browser may require supported full-screen keyboard lock or rebinding. Escape remains available.

New computer rooms use rules version 6. Tracking and previously created rooms retain their prior guard economy. The server, not the renderer, calculates damage and regeneration:

| Defense | Armor above 0 | Armor at 0 |
| --- | --- | --- |
| Correct named side (left against left, right against right) | No HP or armor damage | HP damage × 0.90 |
| Wrong side | Full HP damage; armor unchanged | Full HP damage |
| Both-arm guard | Armor loses the incoming damage; overflow reaches HP | Full HP damage |

Armor gains one point every five active-round seconds, capped at 10. It never regenerates from zero and resets with HP for the next round. Stale or released guard gives no mitigation. HP and feedback preserve decimal damage, so a level-1 hit against correct-side broken guard costs 0.9 HP. The HUD identifies the selected guard and broken armor. Duplicate strike protection, timing, camera-only input boundaries and server ranges remain enforced.

Dash speed increased from 2.6× to 3.0× (about 15% farther), with the same duration, cooldown, duck window and swept collision limits. During high-kick extension, the attacking foot points along the shin instead of inheriting the hip's inward yaw; the planted foot retains its supporting pivot. Both male and female rigs are checked in both directions.

The approved saved avatar now uses compact black/red fingerless MMA gloves with a padded back, wrist strap and modeled curled fingers. Cage-only hand triangles remain hidden to prevent the straight authored fingers poking through. An elbow corrective joint carries the bend's central skin band at half the elbow angle, preserving volume at sharp guard bends. The profile avatar and source asset topology are unchanged.

The lobby fighter faces sideways toward a hanging bag, makes contact during its warm-up and keeps footwork, ground shadows and changing lights. The bag swings around its hanging point. Preview rendering retains its 24-fps cap and hidden/offscreen/reduced-motion handling.

The default fight camera is angled a further 0.22 radians toward the side. Ringside/Overhead buttons are replaced by Lock camera plus the Boxing camera reset. Drag, pinch, wheel and arrow adjustments are ignored while locked, and both camera position and target stay fixed. Unlock restores orbit control; reset restores follow mode. Closer zoom no longer snaps outward past the default distance.

Navigating to another app page suspends input and camera capture while retaining the practice session, online room and camera lock. Returning restarts input, refreshes server state and sequence, and resumes the renderer. A light heartbeat keeps an online room connected while the app remains active; the opponent and round clock continue while away. Explicit Leave match still forfeits. Browser background throttling/network loss can still reach the existing disconnect timeout. Account changes clear the suspended session. API requests time out instead of leaving the input sender stuck indefinitely.

Validation uses disposable local accounts/databases: server guard/regeneration/round-reset tests; controller chords, Ctrl event modifiers, binding migration and Tracking isolation; real male/female kick-toe alignment, elbow/skin weights, arm contact and glove checks; two-client guard/HUD, repeated navigation recovery, locked camera, desktop/mobile layout; full camera championship regression; GET-only exact-revision deployment verification.
