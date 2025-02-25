from ursina import *
from ursina.scripts.smooth_follow import SmoothFollow
from opensimplex import OpenSimplex
import random
from ursina.prefabs.trail_renderer import TrailRenderer
from PIL import Image

app = Ursina()

big_cube_scale = 50
big_cube = Entity(model='cube', scale=big_cube_scale, color=color.light_gray, collider='box')

player = Entity(model='cube', color=color.red, mass=1, y=1)
player.collider = BoxCollider(player)

player_light = PointLight(
    color=color.white,  
    parent=player,  
    position=(0, 4, 0), 
    intensity=2, 
    range = 5 
)

player.shader = Shader(
    language=Shader.GLSL,
    vertex_shader="""
#version 450
in vec4 in_position;
in vec2 in_uv;
in vec3 in_normal;

uniform mat4 model_matrix;
uniform mat4 view_matrix;
uniform mat4 projection_matrix;

out vec2 uv;
out vec3 normal;

void main() {
    gl_Position = projection_matrix * view_matrix * model_matrix * in_position;
    uv = in_uv;
    normal = mat3(model_matrix) * in_normal;
}
""",
    fragment_shader="""
#version 450
in vec2 uv;
in vec3 normal;
out vec4 color;

uniform sampler2D _MainTex;
uniform vec4 _Color;

void main() {
    vec4 texColor = texture(_MainTex, uv);
    vec3 lightDir = normalize(vec3(1, -1, 1)); // Example light direction
    float diffuse = max(dot(normal, lightDir), 0.0);
    color = (texColor * _Color + vec4(1, 0, 0, 0.5)) * (diffuse + 0.2); // Red glow
}
"""
)

speed = 60
gravity = 30
velocity = Vec3(0, 0, 0)

camera.position = (0, 10, -30)
camera.look_at(big_cube)
camera.add_script(SmoothFollow(target=player, offset=[0, 10, -30], speed=4))

edge_threshold = big_cube.scale_x / 2

rotation_speed = 90
rotating = False
target_rotation = 0
rotation_axis = Vec3(0, 0, 0)

translation_duration = 1
translating = False
target_position = Vec3(0, 0, 0)
translation_start_time = 0
translation_axis = Vec3(0, 0, 0)
player_before_translate = Vec3(0, 0, 0)
player_opacity = 1
opacity_change_duration = 0.5
opacity_changing = False
opacity_start_time = 0

current_rotation = 0

objects = []
noise = OpenSimplex(seed=random.randint(0, 10000))

object_fade_in_delay = 0.5
object_fade_in_duration = 1

attack_cooldown = 1.0
last_attack_time = 0
attack_damage_radius = 10
is_attacking = False

slam_jump_height = 3
slam_down_speed = 10
slam_duration = 0.5

game_duration = 60 
time_left = game_duration
timer_text = Text(
    text=f"Time: {time_left:.0f}",
    position=window.top_right + Vec2(-0.1, -0.04),  
    origin=(1, 1),  
    background=True,
    color=color.white,
    backgound_color=color.black,
    padding=(4, 4),
    scale=1.2
)
game_over_text = Text(
    text="GAME OVER",
    position=Vec2(0.15, 0.1),  
    origin=(0.5, 0.5),
    color=color.red,
    scale=2,
    enabled=False 
)

final_score_text = Text(
    text="",  
    position=Vec2(0.15, -0.1),  
    origin=(0.5, 0.5),
    color=color.yellow,
    scale=1.5,
    enabled=False
)

game_active = True  

score = 0
score_text = Text(
    text=f"Score: {score}",
    position=window.top_left + Vec2(0.1, -0.04),  
    origin=(0, 1),  
    background=True,  
    color=color.white, 
    backgound_color=color.black, 
    padding = (4,4), 
    scale = 1.2
)

trail = TrailRenderer(
    parent=player,  
    color=color.white,  
    thickness=0.1,  
    length = 20,
    world_space = False 
)

def reset_object_position(obj):
    x = noise.noise2(obj.seed * 0.5, time.time() * 0.2) * big_cube_scale / 2
    z = noise.noise2(obj.seed * 0.5 + 100, time.time() * 0.2) * big_cube_scale / 2
    y = big_cube_scale / 2 + 0.5

    obj.position = (x, y, z)
    obj.direction = Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)).normalized()  


def generate_objects():
    global objects
    for obj in objects:
        destroy(obj)
    objects = []

    for i in range(random.randint(5,30)):
        x = noise.noise2(i * 0.5, time.time() * 0.2) * big_cube_scale / 2
        z = noise.noise2(i * 0.5 + 100, time.time() * 0.2) * big_cube_scale / 2
        y = big_cube_scale / 2 + 0.5

        scale = abs(noise.noise2(i * 0.5 + 200, time.time() * 0.2)) * 1.5 + 0.5

        color_ = color.random_color()
        model_type = random.choice(['cube', 'sphere', 'cylinder', 'cone'])
        obj = Entity(model=model_type, color=color_, position=(x, y, z), scale=scale, collider='box')
        obj.direction = Vec3(random.uniform(-1, 1), 0, random.uniform(-1, 1)).normalized() 
        obj.alpha = 0
        obj.seed = i
        obj.fade_in_start_time = time.time() + object_fade_in_delay
        objects.append(obj)


generate_objects()

attack_sound = Audio('attack1.mp3', loop=False)  
attack_sound2 = Audio('attack2.mp3', loop=False) 

def attack():
    global last_attack_time, is_attacking, score
    if time.time() - last_attack_time >= attack_cooldown and not is_attacking:
        is_attacking = True
        original_y = player.y

        def slam_attack():
            global is_attacking,score

            for obj in objects:
                distance2 = distance(player,obj)

                if distance2 < attack_damage_radius:
                    print(f"Slammed {obj}!")
                    obj.scale -= 0.2  
                    if obj.scale.x <= 0:
                        destroy(obj)
                        try:
                            objects.remove(obj)  
                            score += 10
                        except:
                            pass
            score_text.text = f"Score: {score}"
            for i in range(15):
                angle = random.uniform(0, 360)
                direction = Vec3(math.cos(math.radians(angle)), 0, math.sin(math.radians(angle))).normalized()
                p = Entity(model='quad', color=color.orange, scale=.2, position=player.position, delay = slam_duration)
                p.animate_position(p.position + direction * 10, duration=slam_duration*2, curve=curve.out_cubic, delay=0.01)  # Small delay
                p.animate_scale(0, duration=slam_duration, curve=curve.out_cubic, delay=slam_duration)  
                destroy(p, delay=slam_duration + 0.01)  

        player.animate('y', player.y + slam_jump_height, duration=0.5, curve=curve.out_cubic) 
        invoke(slam_attack, delay=0)  
        is_attacking = False
        last_attack_time = time.time()

attack2_cooldown = 5  
last_attack2_time = 0
attack2_in_progress = False  


attack2_cooldown_slider = Slider(
    min=0,
    max=attack2_cooldown,
    show_value=False, 
    position=window.bottom_left + Vec2(0.1, 0.1),  
    scale=(1, 1),  
    color=color.blue,
    knob_color=color.lime,
    background_color=color.black
)

ult_ready_text = Text(
    text="ULT READY",
    position=attack2_cooldown_slider.position + Vec2(0.1, 0.1),  
    origin=(0.5, 0), 
    color=color.lime,
    scale=1, 
    enabled=False  
)

def attack2():
    global last_attack2_time, attack2_in_progress, score
    if time.time() - last_attack2_time >= attack2_cooldown and not attack2_in_progress:
        attack2_in_progress = True 
        original_y = player.y

        def slam_attack():
            global attack2_in_progress, score
            player.y = original_y  
            attack2_in_progress = False  

            for obj in objects:
                distance2 = distance(player, obj)

                if distance2 < 50:
                    obj.scale -= 0.2 
                    if obj.scale.x <= 0:
                        destroy(obj)
                        try:
                            objects.remove(obj) 
                            score += 10
                        except:
                            pass
            score_text.text = f"Score: {score}"
            for i in range(30):
                angle = random.uniform(0, 360)
                direction = Vec3(math.cos(math.radians(angle)), 0, math.sin(math.radians(angle))).normalized()
                p = Entity(model='quad', color=color.blue, scale=.2, position=player.position, delay = slam_duration)
                p.animate_position(p.position + direction * 30, duration=slam_duration*3, curve=curve.out_cubic, delay=0.01)  # Small delay
                p.animate_scale(0, duration=slam_duration*3, curve=curve.out_cubic, delay=slam_duration)  # Small delay
                destroy(p, delay=slam_duration*3 + 0.01)  

        player.animate('y', player.y + slam_jump_height+5, duration=1, curve=curve.out_expo)  # Jump
        invoke(slam_attack, delay=0.2)  

        attack2_in_progress = False
        last_attack2_time = time.time()

noise = OpenSimplex(seed=random.randint(0, 10000))

def game_over():
    global game_active,score
    game_active = False  
    game_over_text.enabled = True
    final_score_text.text = f"Final Score: {score}"
    final_score_text.enabled = True
    timer_text.enabled = False 

def update():
    global velocity, translating, target_position, translation_start_time, translation_axis, rotating, current_rotation, target_rotation, rotation_axis, player_opacity, opacity_changing, opacity_start_time, is_attacking, player_before_translate, time_left, game_active



    if game_active:

        time_left -= time.dt
        timer_text.text = f"Time: {max(0, time_left):.0f}" 

        if time_left <= 0:
            game_over()
    velocity.y -= gravity * time.dt

    if player.y < -10:  
        player.position = (0, big_cube_scale / 2 + 1, 0) 
        velocity = Vec3(0, 0, 0) 
        generate_objects() 

    if held_keys['w'] and not is_attacking:
        velocity += player.forward * speed * time.dt
    if held_keys['s'] and not is_attacking:
        velocity -= player.forward * speed * time.dt
    if held_keys['a'] and not is_attacking:
        velocity -= player.right * speed * time.dt
    if held_keys['d'] and not is_attacking:
        velocity += player.right * speed * time.dt

    player.position += velocity * time.dt

    if player.intersects(big_cube).hit:
        if velocity.y < 0:
            velocity.y = 0
            player.y = big_cube.y + big_cube.scale_y / 2 + player.scale_y / 2

    if abs(player.x) > edge_threshold and not rotating:
        generate_objects()
        rotating = True
        rotation_axis = Vec3(0, 0, 1)
        if player.x > 0:
            target_rotation = -90
        else:
            target_rotation = 90


    elif abs(player.z) > edge_threshold and not rotating:
        generate_objects()
        rotating = True
        rotation_axis = Vec3(1, 0, 0)
        if player.z > 0:
            target_rotation = -90
        else:
            target_rotation = 90


    if rotating:
        rotation_amount = rotation_speed * time.dt
        if abs(target_rotation - current_rotation) < rotation_amount:
            big_cube.rotation += rotation_axis * (target_rotation - current_rotation)
            rotating = False
            current_rotation = 0
            big_cube.rotation += rotation_axis * -target_rotation

        else:
            if target_rotation > 0:
                big_cube.rotation += rotation_axis * rotation_amount
                current_rotation += rotation_amount
            else:
                big_cube.rotation += rotation_axis * -rotation_amount
                current_rotation += -rotation_amount

    if abs(player.x) > edge_threshold and not translating:
        translating = True
        translation_axis = Vec3(1, 0, 0)
        if player.x > 0:
            target_position = player.position - Vec3(big_cube.scale_x - 2, 0, 0)
        else:
            target_position = player.position + Vec3(big_cube.scale_x - 2, 0, 0)
        translation_start_time = time.time()
        player_before_translate = player.position
        opacity_changing = True
        opacity_start_time = time.time()
        player_opacity = 1

    elif abs(player.z) > edge_threshold and not translating:
        translating = True
        translation_axis = Vec3(0, 0, 1)
        if player.z > 0:
            target_position = player.position - Vec3(0, 0, big_cube.scale_z - 2)
        else:
            target_position = player.position + Vec3(0, 0, big_cube.scale_z - 2)
        translation_start_time = time.time()
        player_before_translate = player.position

        opacity_changing = True
        opacity_start_time = time.time()
        player_opacity = 1

    if translating:
        elapsed_time = time.time() - translation_start_time
        if elapsed_time <= translation_duration:
            player.position = lerp(player_before_translate, target_position, elapsed_time / translation_duration)

            player_opacity = lerp(1, 0, elapsed_time / translation_duration)
            player.color = color.rgba(player.color.r, player.color.g, player.color.b, player_opacity)

        else:
            translating = False
            player.position = target_position

            opacity_changing = True
            opacity_start_time = time.time()

    if opacity_changing:
        elapsed_time = time.time() - opacity_start_time
        if elapsed_time <= opacity_change_duration:
            player_opacity = lerp(0, 1, elapsed_time / opacity_change_duration)
            player.color = color.rgba(player.color.r, player.color.g, player.color.b, player_opacity)
        else:
            opacity_changing = False
            player_opacity = 1
            player.color = color.rgba(player.color.r, player.color.g, player.color.b, player_opacity)

    for obj in objects:
        obj.position += obj.direction * time.dt * 10  

        if abs(obj.x) > big_cube_scale / 2:
            obj.direction.x *= -1  
        if abs(obj.z) > big_cube_scale / 2:
            obj.direction.z *= -1  

    for obj in objects:
        if time.time() >= obj.fade_in_start_time:
            elapsed_time = time.time() - obj.fade_in_start_time
            if elapsed_time <= object_fade_in_duration:
                obj.alpha = lerp(0, 1, elapsed_time / object_fade_in_duration)
            else:
                obj.alpha = 1

    velocity *= 0.95

    for obj in objects:
        obj.position += obj.direction * time.dt * 10  # Move in their direction

        if abs(obj.x) > big_cube_scale / 2 + 0.5 or abs(obj.z) > big_cube_scale / 2 + 0.5:
            reset_object_position(obj)  

    if attack2_in_progress:
        attack2_cooldown_slider.value = time.time() - last_attack2_time  
        ult_ready_text.enabled = False  
    elif time.time() - last_attack2_time < attack2_cooldown:  
        attack2_cooldown_slider.value = time.time() - last_attack2_time
        ult_ready_text.enabled = False  
    else:
        attack2_cooldown_slider.value = attack2_cooldown   
        ult_ready_text.enabled = True  


    # Attack input
    if held_keys['space']:
        attack_sound.play()
        attack()

    if held_keys['e']:
        attack_sound2.play()
        attack2()

app.run()