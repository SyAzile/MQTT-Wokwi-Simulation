## MQTT-Wokwi-Simulation

Simulating **Message Queuing Telemetry Transport (MQTT)** Protocol using [Wokwi](https://wokwi.com/) Simulator and Mosquitto Broker.


<details open>
<summary>📦 Setup Environment</summary>

- Download and Install [Mosquitto](https://mosquitto.org/download/) Broker for Windows.

- Add Mosquitto to PATH. Default Installation Directory for Mosquitto is:
    ```text
    C:\Program Files\mosquitto
    ```

- Now, Open **Notepad as Administrator** and save the following in the above directory by the name **mosquitto.conf** file.
    ```text
    listener 1883 0.0.0.0
    protocol MQTT
    allow_anonymous true
    log_type all
    log_dest file C:\Program Files\mosquitto\mosquitto.log
    ```
- Verify Installation with `mosquitto -v`.

- Check for Mosquitto Subscriber and Publisher with `mosquitto_sub --version` or `mosquitto_pub --version`.

- Stop **Mosquitto Broker** service in **Services.msc**, if you get an error and re-check `mosquitto -v`.

- Test Basic Connection:
    ```text
    mosquitto_sub -h test.mosquitto.org -t test/connect
    mosquitto_pub -h test.mosquitto.org -t test/connect -m "Hello MQTT!"
    ```
</details>