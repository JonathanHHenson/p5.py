"""p5.js-style camelCase aliases."""

from p5_py.api.global_mode import (
    angle_mode,
    apply_matrix,
    begin_shape,
    bezier_point,
    bezier_tangent,
    bezier_vertex,
    blend,
    blend_mode,
    color_mode,
    create_canvas,
    delta_time,
    display_density,
    ellipse_mode,
    end_shape,
    erase,
    frame_count,
    frame_rate,
    image_mode,
    image_sampling,
    is_looping,
    key,
    key_code,
    key_is_down,
    key_is_pressed,
    lerp_color,
    load_font,
    load_image,
    load_json,
    load_pixels,
    load_strings,
    mouse_button,
    mouse_is_pressed,
    mouse_x,
    mouse_y,
    moved_x,
    moved_y,
    no_erase,
    no_fill,
    no_loop,
    no_smooth,
    no_stroke,
    pixel_array,
    pixel_density,
    pixels,
    pmouse_x,
    pmouse_y,
    quadratic_vertex,
    rect_mode,
    reset_matrix,
    resize_canvas,
    save_canvas,
    save_json,
    save_strings,
    shear_x,
    shear_y,
    stroke_cap,
    stroke_join,
    stroke_weight,
    text_align,
    text_ascent,
    text_descent,
    text_font,
    text_leading,
    text_size,
    text_style,
    text_width,
    touches,
    update_pixels,
)

createCanvas = create_canvas
resizeCanvas = resize_canvas
colorMode = color_mode
lerpColor = lerp_color
noFill = no_fill
noStroke = no_stroke
strokeWeight = stroke_weight
strokeCap = stroke_cap
strokeJoin = stroke_join
ellipseMode = ellipse_mode
rectMode = rect_mode
imageMode = image_mode
imageSampling = image_sampling
beginShape = begin_shape
endShape = end_shape
bezierVertex = bezier_vertex
quadraticVertex = quadratic_vertex
shearX = shear_x
shearY = shear_y
applyMatrix = apply_matrix
resetMatrix = reset_matrix
angleMode = angle_mode
frameRate = frame_rate
frameCount = frame_count
deltaTime = delta_time
pixelDensity = pixel_density
displayDensity = display_density
noLoop = no_loop
noSmooth = no_smooth
isLooping = is_looping
keyIsDown = key_is_down
mouseX = mouse_x
mouseY = mouse_y
pmouseX = pmouse_x
pmouseY = pmouse_y
loadPixels = load_pixels
updatePixels = update_pixels
saveCanvas = save_canvas
loadImage = load_image
loadFont = load_font
loadStrings = load_strings
saveStrings = save_strings
loadJSON = load_json
saveJSON = save_json
textSize = text_size
textFont = text_font
textStyle = text_style
textAlign = text_align
textLeading = text_leading
textWidth = text_width
textAscent = text_ascent
textDescent = text_descent
bezierPoint = bezier_point
bezierTangent = bezier_tangent

blendMode = blend_mode
noErase = no_erase
mouseIsPressed = mouse_is_pressed
mouseButton = mouse_button
movedX = moved_x
movedY = moved_y
keyCode = key_code
keyIsPressed = key_is_pressed
pixelArray = pixel_array

__all__ = [
    "createCanvas",
    "resizeCanvas",
    "colorMode",
    "lerpColor",
    "noFill",
    "noStroke",
    "strokeWeight",
    "strokeCap",
    "strokeJoin",
    "ellipseMode",
    "rectMode",
    "imageMode",
    "imageSampling",
    "beginShape",
    "endShape",
    "bezierVertex",
    "quadraticVertex",
    "shearX",
    "shearY",
    "applyMatrix",
    "resetMatrix",
    "angleMode",
    "frameRate",
    "frameCount",
    "deltaTime",
    "pixelDensity",
    "displayDensity",
    "noLoop",
    "noSmooth",
    "isLooping",
    "keyIsDown",
    "mouseX",
    "mouseY",
    "pmouseX",
    "pmouseY",
    "loadPixels",
    "updatePixels",
    "saveCanvas",
    "loadImage",
    "loadFont",
    "loadStrings",
    "saveStrings",
    "loadJSON",
    "saveJSON",
    "textSize",
    "textFont",
    "textStyle",
    "textAlign",
    "textLeading",
    "textWidth",
    "textAscent",
    "textDescent",
    "bezierPoint",
    "bezierTangent",
    "touches",
    "erase",
    "blend",
    "pixelArray",
    "pixels",
    "keyIsPressed",
    "keyCode",
    "key",
    "movedY",
    "movedX",
    "mouseButton",
    "mouseIsPressed",
    "noErase",
    "blendMode",
]
