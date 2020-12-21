# DisplaceIt
A Blender addon to convert shader displacement to mesh displacement

## About
The displacement in Blender's material output shader node only displaces geometry at render time.

It would be useful to create a procedural displacement with the node system and use that to displace the actual geometry.

My use case for this is to export the displaced mesh so that it can be 3D printed.

## Source

This addon is based on the workflow outlined in the links below but I found it difficult to do manually so I decided to write some code to automate it.

  - [CG Cookie Youtube Video](https://www.youtube.com/watch?v=McALCOr39rY)
  - [CG Cookie Forum Post](https://cgcookie.com/questions/8030-what-s-the-best-way-for-convert-to-mesh)

I have made some modifications to the workflow such as keeping the baked texture within blender rather than exporting to a file. I did not see why that was required.


## Addon Summary
To summarise what the addon does:

  1) Move the displacement output to the surface output
  2) Bake the height texture
  3) Reconnect the original surface output but leave the displacement output unused
  3) Set up a displacement modifier on the object using the baked texture
 
