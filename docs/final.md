---
layout: default
title:  Final Report
---

## Demonstration Video
<iframe width="560" height="315" src="https://www.youtube.com/embed/NbO2JNhUz7Q" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

## Project Summary
Fighting is a very important part of Minecraft gameplay. In survival mode, the player usually needs to eliminate different kinds of mobs to save himself and defend the shelter. In multiplayer mode, the agent will also face the threat of other players. A hardcoded computer agent may easily defeat mobs, but when it faces flexible and intelligent human players, the builtin logic will not be sufficient to handle the variety, thus we applied machine learning algorithms to our smart agent in order to simulate human player reaction as much as possible.

This project was based on Malmo python and reinforcement learning in order to create a smart agent for fighting. We applied the modules from RLlib and started the training by fighting with a hardcoded agent which can attack, defend with shield and use gold apples to recover its health. After our smart agent was able to defeat the hardcoded agent for most of the time, we made it fight with models of itself at previous checkpoints and occasionally the basic agent(so that it doesn't forget it's original baseline) to keep improving its ability. During the self-play procedure, we also tried multiple approaches to fix bugs and compare the effectiveness of our changes.

Our final smart agent reached our goal to be able to defeat both a basic agent that has very capable pvp rules, as well as a player in minecraft, and this marked our success for creating a smart fighting AI for this project. It has learned policies such as sheild breaking, eatting a golden apple when it is low health, as well as a few other pvp based policies. 


## Approach
![](setup.png)

We are currently using the preimplemented version of the Proximal Policy Optimization algorithm trainer from RLLIB to train our agent. Which uses the update<br>
$$L^{CLIP}(\theta)=E[min(r(\theta)A_t, clip(r_t(\theta),1-\epsilon,1+\epsilon)A_t)] $$
Where $$r(\theta) = \frac{\pi_{\theta}(a_t|s_t)}{\pi_{\theta_{old}}(a_t|s_t)}$$ the ratio of the current policy over the old policy<br>
$$A_t = A(s,a) = Q(s,a) - V(s)$$ is the advantage function which is the Q-value subtracted by the Value at a given state.
The clip function will keep the ratio $$r(\theta)$$ between $$[1-\epsilon,1+\epsilon]$$

The environment creates two agents that are across the map from each other with a time limit of 120 seconds and through the use of a path finding algorithm they will always find and look towards each other. The path finding is implemented for both the hardcoded and reinforcement-learning agent as we will mainly be focusing on how the agent will use particular weapons and items.

### Baseline approach
The agent named "Fish" is a rule-based agent using many rule derived from actual PvP strategies. For example, when it is low health use golden apples, if it sees the enemy agent hit them based off of the weapon's cooldown for maximum damage, use a sheild when the enemy agent is close. Here are some more detailed rule:

**Weapon rule:**
- In general, use sword when enemy is using axe or fists, try to interrupt axe attacks
- When enemy is shielding, switch to axe and break shield
- When enemy is using sword, use sword/shield combo
- When low HP or enemy low HP, switch to axe for more damage

**Shield rule:**
- In general, don't hold shield against axe, can hold against other weapons
- When low HP, hold shield at all cost, after baiting attack, counter attack or run

**Golden apple rule:**
- When enemy is wielding axe, heal when HP < 10
- When enemy is wielding sword, heal when HP < 7.5
- Otherwise, heal when HP < 4

The agent named "Puffer" will be the reinforcement learning agent, and we decided to discretize the action space. While the observation space is continuous between 0 and 1.Thus the enemy in range observation will be 0 if the enemy is not in range and 1 otherwise. The health observations will be normalized by dividing by a factor of 20, and the enemy weapon type will be mapped as axe=1, sword=0.75, gapple=0.25, shield=0 (offensive to defensive scale)

**Action Space:**
- Attack
- Switch sword
- Switch axe
- Use golden apple
- Use sheild
- IDLE

**Observation Space:**
- In range of the enemy
- current health (normalized)
- enemy health (normalized)
- enemy weapon type

**Reward Space:**
- change in health at each time step (delta_health - delta_enemy_health)
- large positive reward (+20) if the RL agent was able to kill the other agent

For the training process we saved different models throughout intervals. We wanted the agent to be able to learn to hit and not die immediately to the hard coded agent, so we began training the RL agent with diamond armor against the hard coded agent who had leather armor. After running it over night the agent we loaded the agent but this time switched both the agent's armor to gold in order to have an even match. We once again trained it for a few hours and that is where we are currently at.

### Proposed approaches
In order to further improve our agent which we will call "Puffer", since it is able to beat the basic agent a majority of the time, we decided to implement self-play. This was done by first having Puffer cement its baseline as well as creating a checkpoint that will be 20 episodes prior to the current episode by fighting the basic agent which we will call "Fish" 20 more times. Afterwards we created a policy in which Fish will have a 80% chance to use the previous checkpoint of Puffer or 20% chance to use the basic agent. Puffer will then be trained against Fish and every 20 episodes Fish's model will be updated to a more recent checkpoint. The training then continues until we see that it has learned interesting policies.

Since we are using self-play both agents have the same action and observation space, however for Puffer it will have a reward space since it is being trained. The action, observation, and reward space did not change from the baseline approach however we did try different observations and rewards and saw that the best results came from our original baseline spaces.

### Advantages and disadvantages
Since self-play is built upon having an initial baseline RL agent our proposed approach will take more time and need more data. However, an advantage to using self-play is that the RL agent no longer overfits to the rule-based agent that it has trained against for so long and can learn other techniques that it has never seen before. 

The rules for the baseline approach is very open-ended since we based the rule of the rule-based agent off of what we believed to be a good set of rules for pvp. As a result this can create overfitting to the rule-based agent which means our RL agent will only be able to defeat the rule-based agent. By using self-play the rule-based agent will still be used as a baseline, but the learned policy limitations are no longer bounded by just the rules of the rule-based agent and we should see an increase in different pvp policies that the RL agent will learn.

            
 
## Evaluation
First we will create a hard-coded agent with fixed actions, the AI shall play against it until it is developed enough. Then the AI will fight against its previous self (another agent) continuously to improve the quality. The quantitative evaluation metric of this project will be how often the hard-coded agent is defeated. The baseline should be beating the agent for 50% of matches, which means that the AI has at least the “smartness” of a hard coded agent. We expect it to be improved as it should be able to defeat the agent for over 75% of the plays.<br>
<b>This is a chart of the wins of different checkpoint models throughout the training process. The Agent is trained using self-play and then tested against the basic agent.</b>

![](wins_over_time.png)

From the image above even at checkpoint 20, we already had a good baseline of defeating the rule-based agent and through the process of self-play the RL agent begins to consistently score above 20 wins easily.<br>

<b>This is a chart of the wins to losses of 50 episodes from each of the different combinations of agents battling.</b>
![](winsloss.png)

The highest win rate occuring in the battle between our final agent and the basic agent. Overall our final agent trained on self-play defeats both the basic agent as well as the agent that only trained against the basic agent a majority of the time.

<b>This is a heatmap of the different actions and responses that our final agent had in response to the basic agent.</b>
![](actionmap.png)

The qualitative evaluation will be the agent’s response to different incoming actions: such as shielding or avoiding when being attacked. It is hard to judge the quality of combat, but we will try to make the AI react differently to attacks so the fight can be more exciting.

The above image shows some of the different policies or responses that our RL agent has learned after training. There are a few noticable actions points such as eatting a apple when the oppponent has their sheild up and switching to either a sword or an axe whenever the opponent decides to use their golden apple, which leaves them vulnerable to attacks. Another common policy that it learned was to switch to a sword when the basic agent has an axe which could be because the sword is faster at attacking. Another pattern that can be seen is that the agent prefers to use the sword to attack rather than the axe, while occasionally using the axe and sheild.

Although the heat mapping provides some ideas and data of the qualitative analysis, watching the agent fight in the video  provides a better demonstration of what the self-play agent has learned. 
<b>The bottom screen is the self-play trained agent and the top screen is the basic agent</b>
<iframe width="560" height="315" src="https://www.youtube.com/embed/CMIf6wUIE0U" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>

In the video you can see that the self-play agent will only use the golden apple when it has taken significant damage and tries to block incoming attacks using the sheild. Sometimes the self-play agent will hold out the sword and wait for the basic agent to put down the sheild, but it also decides to break the sheild with an axe and defeat the basic agent with the axe while the basic agent is trying to heal with a golden apple.


## Resources Used
The core of our project is reinforcement learning, we used RLlib to implement it. Assignment 2 of this class provided crucial information to set up the reinforcement learning framework.<br>
multi-agent RLLIB: <https://docs.ray.io/en/master/rllib-env.html#multi-agent-and-hierarchical> <br>
multi-agent RLLIB source code: <https://github.com/ray-project/ray/blob/master/rllib/env/multi_agent_env.py><br>
Project Malmo: <https://microsoft.github.io/malmo/0.30.0/Schemas/Mission.html> <br>
Self-play: <https://openai.com/blog/competitive-self-play/> <br>

