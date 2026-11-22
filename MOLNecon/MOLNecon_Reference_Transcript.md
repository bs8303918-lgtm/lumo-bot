# Reference transcript: "How to Make Viral Animated Shorts Using Claude (Full Workflow)"

Author: Mr omi · length 11:52 · auto-transcribed, lightly cleaned.
Free skill from the video: github.com/mromidev/claude-animated-shorts (MIT).

> We use this video's **measured numbers and method** only. Never its stories, characters or art.

[00:00] Look at these two videos. This one has 29 million views and it's not a one off. That channel is brand new and its last 80 shorts got over 200 million views. The other one, that's mine. And no, it didn't come out of an AI video generator. Claude built it in 3D with code every single frame. In this video, I'll show you exactly how I made this animated short. How I trained Claude on this style frame by frame.

[00:25] What went wrong and how I fixed it and how you can get it too. You're going to get all of that for completely free. Alright, let's get into it. If you've never seen this type of short, it's this. The characters are 2D, but the world around them is 3D. So how do you train Claude to make this? First, you need references. A lot of them. I went to the channel and had Claude download the last 20 shorts in this style. The ones that look this good. Now here's the thing, if you just tell Claude to analyze a video

[00:53] it won't look at every frame. It grabs a few here and there, but a normal video runs at 30 frames per second. And you've probably seen this style all over your feed. Most of those look trash. The reason is the tiny stuff, micro animations, a little camera move, a little shading, a little light. That's what makes it feel real. And you only catch that at 30 frames per second. Every single frame, every camera move, every little change in the light. So that's the main thing I told Claude. Watch all of them at 30 frames per second and check

[01:22] everything: the lighting, the contrast, the shadows, the movement, the effects, the cuts, everything. 20 shorts, about 18 minutes of video, over 32,000 frames, and it came back with a rulebook. So what's the actual workflow behind these shorts? It comes down to three layers: how the script is engineered, how the visuals are constructed, and how Claude measured all of it. First the script. To decode it Claude needed the audio

[01:48] and the first time YouTube handed it the German dub. Classic. So it pulled the original English track and transcribed all 20 itself. And every single one opens like this. A paradox in the very first line. No intro, no setup.

[02:15] Then it escalates. Then comes the pivot, where the real reason comes out. Then the payoff. One last line, and the twist lands. And there's a signature move. 14 of the 20 flip into the explanation with the exact same two words. You see, you see, you see, you see, you see, you see. And the delivery is relentless. Almost four words a second, with basically zero dead air. Second, the visuals. The characters are flat, two dimensional.

[02:40] But they're lit like they physically exist in that world. They catch the key light and they cast real shadows. The world is real 3D geometry, traced with black ink outlines, like a comic book. The colors are heavily saturated. Warm highlights, cool blue shadows. And the lighting follows the story. Warm and bright while it sets things up. Then a deep night blue right as the explanation begins. And the camera almost never cuts. 12 of the 20 have one hard cut or none at all.

[03:06] Instead, the camera physically travels into the next moment. Third, and this is the real secret, how Claude analyzed all of it. It didn't just eyeball it, it wrote its own measuring tool. Every two seconds of video became one contact sheet, 60 frames on a single image, 549 of them. Then, it tracked the camera with phase correlation, measuring how far the image shifts frame by frame. It flagged every hard cut, and it measured the brightness, the contrast and the saturation of

[03:34] every short. That's how it found that in about 80% of the frames, the camera is almost perfectly still. Just tiny drifts. So here's the tip. Don't ask Claude what it thinks of a video. Make it measure. You can't recreate an opinion. You can recreate a number. So now I had the whole blueprint. Now, the story. We made the same type of short but with our own story. Same lighting, same camera, same cuts, same script formula, just our own characters. My first topic was why time seems to slow down when you're in danger.

[04:04] While Claude studied the 20, it noticed one of them already covered the exact same experiment, with 5.7 million views. So, we threw it out and picked a new story, one the channel had never told. 1831. 74 soldiers march across an iron bridge, all in step, and one end of the bridge drops into the river. Before writing a single word, Claude checked every fact. The date, the number of soldiers, even how deep the river was.

[04:30] And that turned into the best joke in the whole short.

[04:33] Luckily, the river was only two feet deep. Unluckily, the river was only two feet deep.

[04:39] Then it wrote the script with the exact formula from the 20, a paradox in the very first line. 74 soldiers knocked down an iron bridge just by walking across it. Then it builds up, then you see, then the twist. After that, Claude started building. At first, it used Blender, same as my very first test. Before any of this, I asked Claude for a quick five second test, just to see the look. Claude designed its own character.

[05:05] A little courier. It grabbed free 3D buildings, made flat cartoon clouds, and matched the camera timing from the channel's frames. There was just one problem. On the third camera push, the camera flew right past the character. So for the bridge, Claude started in Blender again. It tested the ink lines there and drew the whole cast in code. Soldiers, an officer, people from the town, a kid, and a parent. Then I had a hunch. Maybe these shorts are made with three.js. That's 3D built with code

[05:33] right in the browser. Claude checked the frames. Flat characters standing in a real 3D world. three.js can do exactly that. So, it moved everything over. And Remotion turns it into a video, frame by frame. Then it built the world. 37 free 3D models. Trees, rocks, flowers, market stalls, a cart, even a windmill. And every texture. The grass, the cobblestones, the roofs, the water, was painted. Painted by code.

[05:59] The characters got 14 different faces. Laughing, whistling, nervous, shocked. Then the bridge. Two towers, iron chains, and a deck 5 meters wide. 74 soldiers march across it. 4 side by side. Every step makes it bounce. And the bounce keeps growing until it snaps. For the ink lines, Claude wrote its own effect. It finds the edges in the 3D world and draws a black line on them. About an hour after the switch, all 15 shots were working.

[06:26] 2025 frames. But before rendering any video, Claude checked still frames. Good thing it did. In three shots, the camera was stuck inside a house. The trees were teal, and a chain was right in front of everyone's faces. While Claude was fixing that, I put one of our frames next to the original, and it looked cheap.

[06:44] Here's what I told Claude. The original is colorful. High contrast. It looks premium. Ours looks dull. So go analyze it. Frame by frame. Take your time. Use 10 agents if you have to. Just make it as close as you possibly can. And Claude agreed. Ours looked cheap. Then it broke down exactly why. The original has black ink lines on the whole 3D world. Ours had almost none. Their colors are bold with long blue shadows and deep darks. Ours were

[07:12] pastel and flat. Their wood and stone look hand painted. You can see the grain and the dark gaps between the planks. Ours were plain. Their backgrounds are blurry so your eye goes straight to the character. Ours were mostly sharp. And the characters. Theirs have egg shaped heads and thin little limbs. Ours had perfect circle heads and chunky bodies. They looked like clipart pasted on top. And this is where it gets interesting. I asked for 10 agents.

[07:37] And it didn't just throw them at the problem, it built a team. Seven agents to study the gap. One for color, one for the ink lines, one for light and shadows, one for textures, one for the characters, one for depth and framing, and one for motion, the camera and the characters. Each one put the original frames next to ours and measured the difference. No guessing, real numbers. An eighth agent worked on the sound. Then four more agents to rebuild everything. One for the camera,

[08:05] one for the world, one for the characters and one for the final look. But here's the problem. Four agents working on the same project can break each other's work. So Claude gave each one its own copy of the project and each agent owned its own files. Nobody else could touch them. When they were done, Claude merged everything back file by file. So here's the tip. When you use a lot of agents, don't just split the jobs, split the files. Then I gave Claude 10 hours. 10 hours to learn this style and make the finished video.

[08:35] Here's what the 7 agents found. First, the ink lines. The original has black lines on almost 3 out of 4 edges. On ours, the agent found 0. The ink effect was there, but the blur effect ran in the same step and wiped it out. And the blur itself? It was so weak you couldn't see it anywhere. Next, the camera. Ours snapped from one spot to the next in 3 frames. The original glides over about 23 frames. Slow in, slow out.

[09:01] Then the color. The original has no pure black anywhere. Ours went almost black. And at sunset, their shadows are purple. Ours were brown. And the characters. Their bodies are three and a half heads tall. Ours were under three. And our arms and legs were five times too thick. But the agents also found something I didn't expect. Some of our own notes were wrong. Remember the egg shaped heads? The agent measured 38 of them. Their heads are actually rounder than ours.

[09:27] Ours were the egg-shaped ones. And remember the measuring tool from the start? It said the camera is almost still 80% of the time. It's not. The camera is moving in 65% of the frames, slowly pushing in. The tool just couldn't see moves that slow. And this is exactly the part other tutorials skip. I found only two other tutorials on this style. One sells it inside an app, $67 a month or $97 for everything.

[09:53] The other one gives you a few prompts and it says your first results might not look as clean. So here's how you can get mine. Everything from this video, every rule and every fix I saved as one skill for Claude and I'm giving it away fully free on my GitHub. You get the whole repository with 5,000 reference images. The link is in the description. So you don't have to do anything. Just install it and start making videos. Everything is already set up

[10:18] so the output should be as polished as it gets. And I'm going to keep uploading new things there. I'll keep updating it and making it better. And you get all of that for free. And here's one more thing. I'm making a video on it tomorrow. This realistic 3D video. As you can see, I made it. That's my name on it.

[10:35] Here's something wild. Pull every blood vessel out of your body and lay them in one straight line. Most people guess it would reach across a football field. Not even close.

[10:45] Your body hides billions of microscopic tubes branching through every muscle, every organ, even your bones. Lay them all out and the line would leave your city, cross entire countries, stretch over oceans and keep on going. Scientists estimate about 100,000 kilometers. That's enough to wrap around the whole earth roughly two and a half times.

[11:05] Just so you know, I've never seen anything like this made with AI. Other people have made this style with Claude, but not like this. I looked and I couldn't find a single tutorial that gets this close. If this showed up on your feed, you'd never guess AI touched it. In that video, I'll show you exactly how I made it. How to animate a realistic face with an open source AI model. How to rig the character for free on your own computer. How to make the world look real. How to cut the render from 7.5 hours to 1 hour

[11:33] and how to render it smaller, then upscale it so it renders as fast as it gets. You can find the skill and everything in the description. The link to the GitHub repository is right there, completely free. That's all for today. Make sure to subscribe and like. And with this type of workflow, you can pretty much clone any style. Bye.
