# I Have Questions.md

## Subject matter: 
How to create a graphical user interface.

## Body: 
When I was about 10 years old I dug through 'C:/Program Files/' repeatedly in a hope to discover how to make a pop-up window.
What defined the edges of an interface? 
Why do some windows look different than others?
How can I add buttons? 

I was excited. I wanted to make something.

Could I mimick code from a software that was installed on my computer?
I checked each folder in 'C:/Program Files/' looking for clues.

As I searched, the questions changed.
What is a DLL?
Mostly, the only files I could open and inspect were little icons and fuzzy images - Why?

I gave up.
Wait - No I didn't. I am here now.

Honestly, I still don't understand where the edges of the window come from.
The easy answer is: **libraries**.
Many people have done a lot of work to build various GUI libraries, to help people like me (and you) build software.

For this package, the application window is built with Tkinter, which is included in Python's standard library.
You can see how the graphical user interface (GUI) is defined at: https://raw.githubusercontent.com/City-of-Memphis-Wastewater/pdflinkcheck/main/src/pdflinkheck/gui.py

This gui.py file isn't perfect, but exploring it will be far more illuminating than trying to open a DLL file in Notepad.

This is not a recomendation to use Tkinter. I would recommend learning how to build a basic web-stack GUI which can be served locally. 

You might not want to make classic interfaces. 
It is what I grew up with, so I get a tickle when I participate in the tradition of local programs, but web and mobile are super valid.
If you want to make classic interfaces, you should learn about Tauri.
If you write core logic and then expose it in a way that’s friendly to the web, you can then use Tauri to wrap that web interface into something that feels native on your machine.
This sounds wild, to go from native core to web tech back to native distribution, but it makes sense when you figure that: 
- Web stack interfaces (HTML, CSS, TS/JS) offers the most control and best portability of graphics, with lots of people having built tools that you can leverage.
- Making your code accessible via web requests and/or an API will help it have the widest possible reach.

Personally, I get really excited when my Python code can run smoothly on Windows, iOS, Linux, and mostly importantly, as Linux on Android via Termux. Yes, sure, if Android is a target, the same core can be packaged as an Android app and be more accessible. Why do I want Termux? Because it's more about leveraging the machine. Basically, with code that can run on Termux, I can take any old android phone in a drawer and use it like I might use a Raspberry Pi. Tkinter will not run from Termux, not without proot. It is better to start a server on Termux, and then vew the app on localhost through your browser.

Links:
- https://docs.python.org/3/library/tkinter.html
- https://v2.tauri.app/start/
- https://pyo3.rs/main/doc/pyo3_ffi/index.html
- https://bheisler.github.io/post/calling-rust-in-python/

Copyright © 2025 George Clayton Bennett
