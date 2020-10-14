# CubeSat_Concept
Proof of concept of a CubeSat capable of capturing and streaming image to a local server and powered through solar panels and rechargeable batteries.

Description of the script:

With help of Python's 3 http.server module I set up a custom webserver of my own and defined how it responds based on the HTTPrequest and the requested path. This makes it so browsing to my Raspberry Pi directs to the index.html page which I've written into my code as a string for which then a request is send.

In the page there is a reference to the stream.mjpg comming from the camera with help of the PiCamera library which is again delivered in response to a GET request and to which it keep sending frames as long as new frames keep entering the buffer from the camera and as long as the client that requested it still exists.

On the html page there's also a button which sends a post request that users connected to the sat can use to take a pic and tweet it.

Because twitter doesn't allow to upload a pic in an automated fashion and because I don't have a fixed IP adress on the Raspberry Pi from which twitter can access the best way to show it is as a twitter card. The card and picture is handled by taking a pic when the post request arrives, saving it with a unique name based on the time and sending it over FTP to a webserver. An html page is generated as a string which includes a link to the just uploaded pic and which contains all the info for a twitter card and then uploads it as bytes over the same FTP connection to said webserver.

Finally, a popup is opened on the user’s end to a posting page for twitter which will automatically include the link to the uploaded html page.



