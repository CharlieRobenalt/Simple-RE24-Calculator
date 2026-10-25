# Simple RE24 Calculator & Game Report Generator

A Python tool that pulls MLB play-by-play MLB Statcast data from 'pybaseball', and computes **Expected Run Contribution (ERC / RE24) for every plate appearance using the 24 base-out state matrix, and complies a post-game html report.

## Overview 

### The RE24 Formula
Run Expectancy based on the 24 base-out matrix measures how much a batter's plate appearance altered their team's expected runs. 

$$\text{ERC} = \text{Runs Scored} - \text{RE}_{\text{pre}} + \text{RE}_{\text{post}}$$

* **$\text{Runs Scored}$**: Direct runs crossing the plate on the event.
* **$\text{RE}_{\text{pre}}$**: Historical run expectancy of the base-out state prior to the play.
* **$\text{RE}_{\text{post}}$**: Expected runs remaining after the play concludes (set to $0.00$ at 3 outs).

### Matching the Scoreboard
Because every completed half-inning transitions from bases empty, 0 outs ($\text{RE} = 0.48$) to 3 outs ($\text{RE} = 0.00$), the sum of Raw ERC:

$$\sum \text{Raw ERC} = \text{Actual Runs} - 0.48 \times (\text{Innings Batted})$$

Adding $+0.48$ per inning batted adjusts the total expected runs to match actual runs scored on the scoreboard over complete games.

