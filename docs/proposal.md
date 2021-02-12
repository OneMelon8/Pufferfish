---
layout: default
title:  Proposal
---

## Abstract
We decided to create a reinforcement learning agent that specializes in player-versus-player combat using different weapons. The agent will perform different action choices such as hitting with an axe, sword, blocking with a sheild and eatting a golden apple. We will first train the RL agent against a hand-coded policy based agent that will choose actions based on what we think are good decisions, such as eatting a golden apple at low hp, removing a player's sheild by hitting with an axe, and etc. After training against a hand-coded agent and performing well against it, we will make the RL agent learn to pvp based on self-play. The goal is through self-play the RL agent will become good enough at PVP to defeat a human player. 


## AI/ML Algorithms
We plan to use a prebuilt PPO reinforcement algorithm from RLLIB in order to train the agent to defeat the hand-coded agent. After defeating the hand-coded agent we plan to use self-play in order to further train the RL agent to learn. If the RL agent ends up performing worse from self play we plan to add additional policies to our general AI hand-coded agent.


## Evaluation Plan
Firstly we will create a hard-coded agent with fixed actions, the AI shall play against it until it is developed enough. Then the AI will fight against itself (another agent) continuously to improve the quality. The quantitative evaluation metric of this project will be how often the hard-coded agent is defeated. The baseline should be beating the agent for 50% of matches, which means that the AI has at least the “smartness” of a hard coded agent. We expect it to be improved as it should be able to defeat the agent for over 75% of the plays.

The qualitative evaluation will be the agent’s response to different incoming actions: such as shielding or avoiding when being attacked. It is hard to judge the quality of combat, but we will try to make the AI react differently to attacks so the fight can be more exciting.


## Meeting Time (Per Week)
Every Friday 18:00 Irvine time
Schedule extra if needed
