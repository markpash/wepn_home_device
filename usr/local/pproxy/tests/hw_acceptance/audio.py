import pygame
pygame.init()
pygame.mixer.init(frequency = 44100, size = -16, channels = 2, buffer = 2**12) 

pygame.mixer.music.load("leftchannel.wav")
pygame.mixer.music.play()
pygame.event.wait()
