# Closed gloves and coordinated body motion

Both fighters now wear closed red boxing gloves. Cage-only geometry under each glove is removed from rendered triangles, preventing fingers from poking through while preserving the original avatar assets and profile appearance.

Visible hips, knees and ankles guide weight shift, crouching and stance. The pelvis can translate and rotate while fixed-length legs keep feet planted and ankle joints keep them level. When legs leave the frame, the added tracking fades back to upper-body controls. No kicks or knee attacks are added.

Punches directed at the camera recover foreshortened depth from previously observed arm lengths when both segments and forward motion support the inference. Short bent jabs retain their shape; contact with the bag/opponent still constrains the arms. This is a single-camera estimate, not measured motion-capture accuracy.

Forward leaning or nodding now requests walking more easily. Combine forward/backward lean with left/right lean for all four diagonals. Hold the first direction for two seconds; then change direction continuously. Return upright to stop. A brief bow remains evasion, while a pure vertical crouch does not walk.

- [Closed red gloves and arena](arena-desktop.png)
- [Mobile camera](arena-mobile.png)
- [Back extension](back-extension.png)
- [Shoulder wind-up](shoulder-windup.png)
- [Full arm reach](full-punch.png)

Screenshots use the actual approved avatars with synthetic landmarks in local Chromium. Tests cover both avatar genders, planted and level feet during weight shift, fixed bone lengths, normalized skin weights, removed finger triangles, lower-body validation/synchronization and occlusion fallback, foreshortened frontal punches, four diagonal directions, contact and the full championship flow. Physical webcam accuracy still requires testing with the user's framing and lighting. Recalibrate standing upright with hands visible; include hips, knees and ankles if possible.
