python3 device_test.py
read -p "Press any key for LCD test" -n1 -s
python3 test_lcd.py
read -p "Press any key for temperature test" -n1 -s
python3 test_temperature.py
read -p "Press any key for buttons test" -n1 -s
python3 test_buttons.py

