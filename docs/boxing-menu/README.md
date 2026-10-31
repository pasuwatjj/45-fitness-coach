# Boxing mode menu

The entry screen offers Training and Fight a friend. It loads generated gym artwork and real localized HTML buttons; it does not open a camera or construct a WebGL arena before mode selection. The illustrated characters are menu art, not replacements for the player's saved Quaternius fighter.

Training enters the bag arena and requests camera permission. Friend mode shows the existing confirmed-friend invitation flow. After acceptance, both cameras must detect a calibrated pose before automatic readiness starts the server's five-second countdown. No random matchmaking or AI opponent is advertised.

Back to Choose mode stops camera tracks, clears the scene, and leaves any open match. Permission denial retains an explicit camera retry control. Empty friend lists link to the existing Friends page. Incoming invitations can enter the friend lobby directly.

Artwork: original generated background at `static/images/boxing/mode-menu.png`. All headings, descriptions, controls, and waiting states are HTML, not baked into the image. Desktop and mobile menu captures are alongside this document.

Validation: `tests/qa_boxing_menu.py` uses disposable local accounts and synthetic camera landmarks to cover both modes, invitation acceptance, automatic countdown, two-client hit synchronization, timer visibility, permission denial, empty friend lists, and cleanup. It does not measure recognition accuracy on real users. The existing pose fixtures and championship regression cover gameplay separately.
