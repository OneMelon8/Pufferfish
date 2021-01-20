---
layout: default
title:  Proposal
---

## Abstract
We decided to create an agent that specializes in player-versus-player combat using different weapons. We will train two agents that will fight each other on randomly-generated maps. The agent will take in observation from the world consisting of enemy position, current health, and current position, hotbar index. We plan to have several actions, including attack, shield, jump, move_to(position), look_at(position), switch_hotbar(index), use_item, etc.


## AI/ML Algorithms
We plan to test two different reinforcement learning agents, one trained using a DQN model and the other trained using the Actor critic model.


## Evaluation Plan
Firstly we will create a hard-coded agent with fixed actions, the AI shall play against it until it is developed enough. Then the AI will fight against itself (another agent) continuously to improve the quality. The quantitative evaluation metric of this project will be how often the hard-coded agent is defeated. The baseline should be beating the agent for 50% of matches, which means that the AI has at least the “smartness” of a hard coded agent. We expect it to be improved as it should be able to defeat the agent for over 75% of the plays.

The qualitative evaluation will be the agent’s response to different incoming actions: such as shielding or avoiding when being attacked. It is hard to judge the quality of combat, but we will try to make the AI react differently to attacks so the fight can be more exciting.


## Meeting Time (Per Week)
Every Friday 18:00 Irvine time
Schedule extra if needed
