// === Sensor pins ===
const int logicAPin = 4;    // Digital pin for logic sensor A
const int logicBPin = 5;    // Digital pin for logic sensor B
const int analogPin = A0;   // Analog pin for analog sensor

// === Relay control pins ===
const int relay1Pin = 7;    // Digital pin controlling Relay 1
const int relay2Pin = 8;    // Digital pin controlling Relay 2
const int relay3Pin = 9;    // Digital pin controlling Relay 3

// === Moving average buffer for analog sensor ===
const int numReadings = 200;    // Number of readings to average
int readings[numReadings];      // Array to store analog readings
int readIndex = 0;              // Index for current reading
long total = 0;                 // Running total of readings
int averageAnalog = 0;          // Calculated average analog value

// === Timing constants ===
const unsigned long preRelayDelay = 7000;          // Delay before relay sequence starts (ms)
const unsigned long blockedCooldown = 40000;       // Cooldown period after blocked detection (ms)

// === Relay timing constants ===
const unsigned long relay1Duration = 100;          // Relay 1 ON duration (ms)
const unsigned long relay1ToRelay2Delay = 1000;      // Delay between Relay 1 OFF and Relay 2 ON (ms)
const unsigned long relay2Duration = 100;          // Relay 2 ON duration (ms)
const unsigned long sequenceDelay = 5000;           // Delay between repeated relay cycles (ms)
const unsigned long relay3Duration = 1000;          // Final Relay 3 ON duration (ms)
const int relayCycles = 1;                          // Number of cycles for Relay 1 and 2 sequence

// === Timing state variables ===
unsigned long lastBlockedTime = 0;       // Timestamp of last blocked condition
unsigned long stateStartTime = 0;        // Timestamp when current relay state started
unsigned long currentTime = 0;           // Current time from millis()
unsigned long relayCycleStart = 0;       // Timestamp when full relay cycle started

// === State machine for relay control ===
enum RelayState {
  IDLE,              // System is idle
  PRE_RELAY_DELAY,   // Waiting before starting relay sequence
  RELAY1_ON,         // Turning on Relay 1
  RELAY1_WAIT,       // Waiting while Relay 1 is ON
  RELAY2_ON,         // Turning on Relay 2
  RELAY2_WAIT,       // Waiting while Relay 2 is ON
  SEQUENCE_DELAY,    // Delay between repeated cycles
  RELAY3_ON,         // Final Relay 3 ON
  RELAY3_WAIT,       // Waiting while Relay 3 is ON
  COMPLETE           // Sequence complete
};

RelayState relayState = IDLE;     // Initial state
bool wasBlocked = false;          // Previous blocked state
int sequenceCount = 0;            // Counter for relay cycles

void setup() {
  Serial.begin(115200);           // Start serial communication for debugging

  // Configure sensor pins
  pinMode(logicAPin, INPUT_PULLUP);   // Enable pull-up resistor for logic sensor A
  pinMode(logicBPin, INPUT_PULLUP);   // Enable pull-up resistor for logic sensor B
  pinMode(analogPin, INPUT);          // Analog input pin

  // Configure relay control pins
  pinMode(relay1Pin, OUTPUT);
  pinMode(relay2Pin, OUTPUT);
  pinMode(relay3Pin, OUTPUT);

  // Ensure all relays are initially OFF
  digitalWrite(relay1Pin, LOW);
  digitalWrite(relay2Pin, LOW);
  digitalWrite(relay3Pin, LOW);

  // Initialize readings buffer with zeros
  for (int i = 0; i < numReadings; i++) {
    readings[i] = 0;
  }
}

void loop() {
  // === Read sensors ===
  int logicA = digitalRead(logicAPin);          // Read logic sensor A
  int logicB = digitalRead(logicBPin);          // Read logic sensor B
  int analogValue = analogRead(analogPin);      // Read analog sensor

  // === Update moving average ===
  total -= readings[readIndex];                 // Subtract old reading
  readings[readIndex] = analogValue;            // Add new reading
  total += readings[readIndex];                 // Update total
  readIndex = (readIndex + 1) % numReadings;    // Move to next index
  averageAnalog = total / numReadings;          // Compute average

  // === Calculate expected total relay duration ===
  unsigned long perCycleDuration = relay1Duration + relay1ToRelay2Delay + relay2Duration; // Time for one Relay 1/2 cycle
  unsigned long repeatedCyclesDuration = (relayCycles - 1) * (perCycleDuration + sequenceDelay) + perCycleDuration; // All cycles combined
  unsigned long totalExpected = repeatedCyclesDuration + relay3Duration;  // Full sequence duration

  // === Print sensor values and expected time ===
  Serial.print("Analog A0: ");
  Serial.print(analogValue);
  Serial.print(" | Average: ");
  Serial.print(averageAnalog);
  Serial.print(" | Expected Relay Duration: ");
  Serial.print(totalExpected / 1000.0, 2);  // Print in seconds with 2 decimal places
  Serial.println(" s");

  // === Blocked detection logic ===
  bool isBlocked = (logicA == 0 && logicB == 1) || (analogValue < (averageAnalog - 15));  // Define blocked condition
  currentTime = millis();  // Get current time

  // Trigger relay cycle if blocked condition just occurred
  if (isBlocked && !wasBlocked && (currentTime - lastBlockedTime >= blockedCooldown)) {
    Serial.println("Completely Blocked - Starting Relay Cycle");

    // Begin the relay sequence
    if (relayState == IDLE) {
      relayState = PRE_RELAY_DELAY;
      stateStartTime = currentTime;
      sequenceCount = 0;
      relayCycleStart = currentTime;  // Record cycle start time
    }

    lastBlockedTime = currentTime;  // Update cooldown timer
  }

  wasBlocked = isBlocked;  // Save state for next loop

  // === Relay sequence state machine ===
  switch (relayState) {
    case PRE_RELAY_DELAY:
      // Wait for pre-relay delay before starting sequence
      if (currentTime - stateStartTime >= preRelayDelay) {
        relayState = RELAY1_ON;
        stateStartTime = currentTime;
      }
      break;

    case RELAY1_ON:
      // Turn ON Relay 1
      digitalWrite(relay1Pin, HIGH);
      stateStartTime = currentTime;
      relayState = RELAY1_WAIT;
      break;

    case RELAY1_WAIT:
      // Wait for Relay 1 duration, then turn it OFF
      if (currentTime - stateStartTime >= relay1Duration) {
        digitalWrite(relay1Pin, LOW);
        stateStartTime = currentTime;
        relayState = RELAY2_ON;
      }
      break;

    case RELAY2_ON:
      // Short delay after Relay 1 before Relay 2 turns ON
      if (currentTime - stateStartTime >= relay1ToRelay2Delay) {
        digitalWrite(relay2Pin, HIGH);
        stateStartTime = currentTime;
        relayState = RELAY2_WAIT;
      }
      break;

    case RELAY2_WAIT:
      // Wait for Relay 2 duration, then turn it OFF
      if (currentTime - stateStartTime >= relay2Duration) {
        digitalWrite(relay2Pin, LOW);
        sequenceCount++;  // Track how many times we've repeated this

        if (sequenceCount < relayCycles) {
          // Delay before repeating Relay 1/2 cycle
          stateStartTime = currentTime;
          relayState = SEQUENCE_DELAY;
        } else {
          // All cycles done, move to final step
          relayState = RELAY3_ON;
          stateStartTime = currentTime;
        }
      }
      break;

    case SEQUENCE_DELAY:
      // Delay between repeated Relay 1/2 cycles
      if (currentTime - stateStartTime >= sequenceDelay) {
        relayState = RELAY1_ON;
        stateStartTime = currentTime;
      }
      break;

    case RELAY3_ON:
      // Turn ON final Relay 3
      digitalWrite(relay3Pin, HIGH);
      stateStartTime = currentTime;
      relayState = RELAY3_WAIT;
      break;

    case RELAY3_WAIT:
      // Wait for Relay 3 duration, then turn it OFF
      if (currentTime - stateStartTime >= relay3Duration) {
        digitalWrite(relay3Pin, LOW);
        relayState = COMPLETE;
      }
      break;

    case COMPLETE:
      // Print actual elapsed time for the whole sequence
      Serial.print("Relay cycle complete. Actual duration: ");
      Serial.print((currentTime - relayCycleStart) / 1000.0, 2);  // Seconds
      Serial.println(" s");
      relayState = IDLE;  // Go back to idle
      break;

    case IDLE:
    default:
      // Do nothing while idle
      break;
  }

  delay(100);  // Short delay to reduce CPU load and control print rate