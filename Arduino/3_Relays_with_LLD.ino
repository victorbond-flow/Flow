// === Sensor pins ===
const int analogPin = A0;      // LLD analog sensor

// === Relay control pins ===
const int relay1Pin = 7;       // A→B switch
const int relay2Pin = 8;       // B→A reset
const int relay3Pin = 9;       // Start HPLC run

// === Detection thresholds ===
const int gasThreshold = 200;       // Below this = gas
const int solventThreshold = 500;   // Above this = solvent
const int requiredSolventReads = 5; // Number of solvent readings to confirm slug

// === Timing constants ===
const unsigned long cooldown = 40000;
const unsigned long relay1Duration = 100;
const unsigned long relay1ToRelay2Delay = 2000;
const unsigned long relay2Duration = 100;
const unsigned long relay2ToRelay3Delay = 2000;
const unsigned long relay3Duration = 100;

unsigned long lastTriggerTime = 0;
unsigned long stateStartTime = 0;
unsigned long currentTime = 0;

// === Detection state ===
bool slugComing = false;
int solventCounter = 0;

// === State machine ===
enum RelayState { IDLE, RELAY1_ON, RELAY1_WAIT, RELAY2_ON, RELAY2_WAIT, RELAY3_ON, RELAY3_WAIT, COMPLETE };
RelayState relayState = IDLE;

void setup() {

  Serial.begin(115200);

  pinMode(analogPin, INPUT);
  pinMode(relay1Pin, OUTPUT);
  pinMode(relay2Pin, OUTPUT);
  pinMode(relay3Pin, OUTPUT);

  digitalWrite(relay1Pin, LOW);
  digitalWrite(relay2Pin, LOW);
  digitalWrite(relay3Pin, LOW);
}

void loop() {

  int analogValue = analogRead(analogPin);
  currentTime = millis();

  Serial.print("Analog A0:");
  Serial.println(analogValue);

  bool risingEdgeDetected = false;

  // === Detect gas ===
  if (analogValue < gasThreshold) {
    slugComing = true;
    solventCounter = 0;
  }

  // === Detect solvent after gas ===
  if (slugComing && analogValue > solventThreshold) {
    solventCounter++;
  }

  // === Confirm solvent return ===
  if (slugComing && solventCounter >= requiredSolventReads) {

    if (currentTime - lastTriggerTime >= cooldown) {
      risingEdgeDetected = true;
      lastTriggerTime = currentTime;
      Serial.println("Slug detected - triggering relay sequence");
    }

    slugComing = false;
    solventCounter = 0;
  }

  // === Relay sequence ===
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
      relayState = IDLE;
      break;
  }

  delay(50);
}