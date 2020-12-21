# DisplaceIt
A Blender addon to convert shader displacement to mesh displacement

## About
The displacement in Blender's material output shader node only displaces geometry at render time.

It would be useful to create a procedural displacement with the node system and use that to displace the actual geometry.

My use case for this is to export the displaced mesh so that it can be 3D printed.

## Install
1) Download the zip file attached to the release and extract to somewhere on your computer
2) Open the preferences dialog in blender and then select the add-ons tab
3) Press the install button on the top right
3) Navigate to and select the `displace_it.py` file
3) Search for and enable DisplaceIt in the add-ons dialog

## Usage
1) Add a displacement output in the materials used by the objects you wish to apply this operation to
2) Add geometry to the mesh so that it has something to displace. I used a multi-resolution modifier with a level around 6-8
3) Select the objects that you want to apply the operation to
4) I would suggest opening the terminal using `Window > Toggle System Console` to monitor progress
5) Run the operation from the menu `Object > DisplaceIt`. This step may take a while
6) Tweak the settings to your liking and click off to confirm.

## Options
- Inplace - if ticked will apply the deformation to the selected object. If unticked will create a copy and modify that.
- Resolution - The pixel resolution of the baked image.

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
 
