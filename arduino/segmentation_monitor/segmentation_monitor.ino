const int sensorPin = A0;

unsigned long lastTime = 0;
const int sampleInterval = 20; // milliseconds

void setup() {
  Serial.begin(115200);
}

void loop() {

  unsigned long currentTime = millis();

  if (currentTime - lastTime >= sampleInterval) {

    int value = analogRead(sensorPin);

    Serial.print(currentTime);
    Serial.print(",");
    Serial.println(value);

    lastTime = currentTime;
  }

}