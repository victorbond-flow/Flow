// === Relay control pins ===
const int relay1Pin = 7;       // A→B switch
const int relay2Pin = 8;       // B→A reset
const int relay3Pin = 9;       // Start HPLC run

// === Timing constants (all in ms) ===
const unsigned long cutInterval = 300000;      // 5 minutes between cuts
const unsigned long relay1Duration = 100;
const unsigned long relay1ToRelay2Delay = 500;
const unsigned long relay2Duration = 100;
const unsigned long relay2ToRelay3Delay = 1472;
const unsigned long relay3Duration = 100;

// === State machine ===
enum RelayState { IDLE, RELAY1_ON, RELAY1_WAIT, RELAY2_ON, RELAY2_WAIT, RELAY3_ON, RELAY3_WAIT, COMPLETE };
RelayState relayState = IDLE;

unsigned long stateStartTime = 0;
unsigned long currentTime = 0;
unsigned long lastCutTime = 0;

bool sequenceRunning = false;
int cutCount = 0;
const int totalCuts = 6;

void setup() {
  Serial.begin(115200);

  pinMode(relay1Pin, OUTPUT);
  pinMode(relay2Pin, OUTPUT);
  pinMode(relay3Pin, OUTPUT);

  digitalWrite(relay1Pin, LOW);
  digitalWrite(relay2Pin, LOW);
  digitalWrite(relay3Pin, LOW);

  Serial.println("Ready. Send 's' to start cut sequence.");
}

void loop() {
  currentTime = millis();

  // === Serial trigger ===
  if (Serial.available() > 0) {
    char incoming = Serial.read();
    if (incoming == 's' && !sequenceRunning && relayState == IDLE) {
      sequenceRunning = true;
      cutCount = 0;
      lastCutTime = currentTime - cutInterval; // fire first cut immediately
      Serial.println("Sequence started.");
    }
  }

  // === Cut timing ===
  if (sequenceRunning && relayState == IDLE && cutCount < totalCuts) {
    if (currentTime - lastCutTime >= cutInterval) {
      lastCutTime = currentTime;
      cutCount++;
      Serial.print("Triggering cut ");
      Serial.print(cutCount);
      Serial.print(" of ");
      Serial.println(totalCuts);
      relayState = RELAY1_ON;
      stateStartTime = currentTime;
    }
  }

  // === Stop after totalCuts ===
  if (sequenceRunning && cutCount >= totalCuts && relayState == IDLE) {
    sequenceRunning = false;
    Serial.println("All cuts complete. System idle.");
  }

  // === Relay state machine ===
  switch (relayState) {

    case IDLE:
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
}