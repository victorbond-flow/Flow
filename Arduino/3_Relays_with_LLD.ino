// === Sensor pins ===
const int analogPin = A0;      // LLD analog sensor

// === Relay control pins ===
const int relay1Pin = 7;       // A→B switch
const int relay2Pin = 8;       // B→A reset
const int relay3Pin = 9;       // Start HPLC run

// === Moving average ===
const int numReadings = 200;
int readings[numReadings];
int readIndex = 0;
long total = 0;
int averageAnalog = 0;

// === Timing constants ===
const unsigned long cooldown = 40000;      // Lockout after trigger
const unsigned long relay1Duration = 100;
const unsigned long relay1ToRelay2Delay = 1000;
const unsigned long relay2Duration = 100;
const unsigned long relay2ToRelay3Delay = 2000; // Delay for heart cut to reach column
const unsigned long relay3Duration = 1000;

unsigned long lastTriggerTime = 0;
unsigned long stateStartTime = 0;
unsigned long currentTime = 0;

// === State machine ===
enum RelayState { IDLE, RELAY1_ON, RELAY1_WAIT, RELAY2_ON, RELAY2_WAIT, RELAY3_ON, RELAY3_WAIT, COMPLETE };
RelayState relayState = IDLE;

// === Rising-edge detection ===
bool previousLow = false; // true if previous signal was low (nitrogen)
const int lowThreshold = 300;   // Signal below this = nitrogen
const int highThreshold = 450;  // Signal above this = reaction slug

// --- Persistence filtering and hysteresis ---
int lowAnalogCounter = 0;           // Count consecutive low readings
const int requiredLowSamples = 3;   // Number of consecutive low readings to trigger relays
bool analogBlockedState = false;    // True if currently in a low slug (nitrogen)

void setup() {
  Serial.begin(115200);
  pinMode(analogPin, INPUT);
  pinMode(relay1Pin, OUTPUT);
  pinMode(relay2Pin, OUTPUT);
  pinMode(relay3Pin, OUTPUT);

  digitalWrite(relay1Pin, LOW);
  digitalWrite(relay2Pin, LOW);
  digitalWrite(relay3Pin, LOW);

  for (int i = 0; i < numReadings; i++) readings[i] = 0;
}

void loop() {
  // --- Read analog sensor ---
  int analogValue = analogRead(analogPin);

  // --- Update moving average ---
  total -= readings[readIndex];
  readings[readIndex] = analogValue;
  total += readings[readIndex];
  readIndex = (readIndex + 1) % numReadings;
  averageAnalog = total / numReadings;

  currentTime = millis();

  // --- Print sensor values every loop ---
  Serial.print("Analog A0:");
  Serial.print(analogValue);
  Serial.print(" | Average: ");
  Serial.print(averageAnalog);
  Serial.println();

  // --- Persistence filter & hysteresis ---
int blockLevel = highThreshold - 50;  // low -> high transition threshold, adjust if needed
int unblockLevel = highThreshold - 20; // signal must rise above this to reset

// Count consecutive low readings for glitch rejection
if (!analogBlockedState) {
    if (averageAnalog < lowThreshold) {
        lowAnalogCounter++;
    } else {
        lowAnalogCounter = 0;
    }

    // Confirm “blocked” only after several consecutive lows
    if (lowAnalogCounter >= requiredLowSamples) {
        analogBlockedState = true;
        lowAnalogCounter = 0;
    }
} else { // Currently blocked
    // Clear blocked state only if signal clearly rises above unblock threshold
    if (averageAnalog > unblockLevel) {
        analogBlockedState = false;
    }
}

// --- Detect rising edge for relay trigger ---
bool risingEdgeDetected = false;
if (analogBlockedState == false && previousLow == true && averageAnalog > highThreshold) {
    // Rising edge detected
    if (currentTime - lastTriggerTime >= cooldown) {
        risingEdgeDetected = true;
        lastTriggerTime = currentTime;
        Serial.println("Rising edge detected - triggering sequence");
    }
}

// Update previousLow for next loop iteration
previousLow = (averageAnalog < lowThreshold);

  // --- Relay sequence ---
  switch (relayState) {
    case IDLE:
      if (risingEdgeDetected) {
        relayState = RELAY1_ON;
        stateStartTime = currentTime;
      }
      break;

    case RELAY1_ON:
      digitalWrite(relay1Pin, HIGH);
      stateStartTime = currentTime;
      relayState = RELAY1_WAIT;
      break;

    case RELAY1_WAIT:
      if (currentTime - stateStartTime >= relay1Duration) {
        digitalWrite(relay1Pin, LOW);
        stateStartTime = currentTime;
        relayState = RELAY2_ON;
      }
      break;

    case RELAY2_ON:
      if (currentTime - stateStartTime >= relay1ToRelay2Delay) {
        digitalWrite(relay2Pin, HIGH);
        stateStartTime = currentTime;
        relayState = RELAY2_WAIT;
      }
      break;

    case RELAY2_WAIT:
      if (currentTime - stateStartTime >= relay2Duration) {
        digitalWrite(relay2Pin, LOW);
        stateStartTime = currentTime;
        relayState = RELAY3_ON;
      }
      break;

    case RELAY3_ON:
      if (currentTime - stateStartTime >= relay2ToRelay3Delay) {
        digitalWrite(relay3Pin, HIGH);
        stateStartTime = currentTime;
        relayState = RELAY3_WAIT;
      }
      break;

    case RELAY3_WAIT:
      if (currentTime - stateStartTime >= relay3Duration) {
        digitalWrite(relay3Pin, LOW);
        relayState = COMPLETE;
      }
      break;

    case COMPLETE:
      relayState = IDLE; // Back to idle
      break;
  }

  delay(100); // Short delay for loop
}