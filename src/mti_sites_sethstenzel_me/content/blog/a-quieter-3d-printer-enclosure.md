---
title: A Quieter 3D Printer Enclosure
date: 2026-04-11
image: /content/images/blog/printer-enclosure.png
tags: [hardware, 3d-printing, raspberry-pi, python]
draft: false
---

The printer lives about four feet from my desk, which was fine until I started
running twelve-hour prints during work hours. The noise is not loud so much as
constant: stepper whine, part-cooling fan, and the power supply fan all sitting in
the same irritating frequency band.

## What actually made noise

Before buying anything I spent an evening with a phone decibel meter and a lot of
patience, turning things off one at a time. The results were not what I expected:

- Part cooling fan: the single largest contributor by a wide margin.
- Power supply fan: second, and running at full speed regardless of load.
- Stepper motors: audible, but mostly as a tone rather than volume.
- Frame resonance: negligible once the printer sat on a paving slab.

The lesson was that the enclosure was the wrong first move. Swapping both fans for
quieter models bought more than half the improvement I was after, for about fifteen
dollars, and it took an hour.

## The enclosure

The enclosure itself is a 2020 extrusion frame with 3mm acrylic panels and a strip
of automotive door seal around the door. Nothing clever. The one detail worth
copying is the exhaust: a 120mm fan pulling through a carbon filter, ducted out the
back, running only while the hotend is above 60C. That keeps the chamber from
cooking the electronics and vents the ABS fumes I had been ignoring.

Control is a Raspberry Pi Zero 2 W reading a DHT22 and driving the fan through a
MOSFET. The whole control loop is about as simple as it sounds — read, compare,
switch, sleep — and it has run without intervention since March.

## Was it worth it

For noise, partly. The enclosure knocked off another few decibels and, more usefully,
changed the character of the sound from a whine to a hum you stop noticing. For print
quality with ABS and ASA, absolutely — warping went from a constant background
annoyance to something I have not thought about in two months.

If you are considering the same project: measure first, replace the fans, and only
then decide whether you still want to build a box.
