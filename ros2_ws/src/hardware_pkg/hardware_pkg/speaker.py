import time
from gpiozero import OutputDevice
from robot_hat.music import Music
from robot_hat import __device__

def main():
    print("Enabling speaker GPIO...")
    spk_en = OutputDevice(__device__.spk_en)
    spk_en.on()
    time.sleep(0.1)

    print("Creating Music object...")
    music = Music()
    print("Mixer init:", music.pygame.mixer.get_init())

    print("Starting playback...")
    music.music_play("/home/robocar/elec-392-project-blekinge-12/sound/realgone.wav", volume=100)

    print("Waiting while music plays...")
    while music.pygame.mixer.music.get_busy():
        print("still playing...")
        time.sleep(0.5)

    print("Done.")

if __name__ == "__main__":
    main()