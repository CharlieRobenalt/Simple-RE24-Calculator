# Simple RE24 Calculator & Game Report Generator

A Python tool that pulls MLB play-by-play MLB Statcast data from 'pybaseball', and computes **Expected Run Contribution (ERC / RE24) for every plate appearance using the 24 base-out state matrix, and complies a post-game html report.

## Overview 

### 1. The RE24 Formula
Run Expectancy based on the 24 base-out matrix measures how much a batter's plate appearance altered their team's expected runs. 

$$\text{ERC} = \text{Runs Scored} - \text{RE}_{\text{pre}} + \text{RE}_{\text{post}}$$

$
