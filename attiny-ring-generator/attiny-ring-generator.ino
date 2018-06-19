int inputPin = 1;
int forwardReversePin = 3;
int ringModePin = 4;

int THRESHOLD = 512;
int RING_DELAY = 50;

void setup() {
  // put your setup code here, to run once:
  pinMode(forwardReversePin, OUTPUT);
  pinMode(ringModePin, OUTPUT);
}

boolean shouldRing = false;
boolean isHigh = false;
int ringIterationCounter = 0;
boolean ringPhase = false;
void loop() {
  // determine if we want to ring the phone based on the input pin
  boolean currentShouldRing = analogRead(inputPin) > THRESHOLD;
  if (!shouldRing && currentShouldRing) {
    shouldRing = true;
    isHigh = true;
    ringIterationCounter = 0;
    ringPhase = true;
  }
  else if (shouldRing && !currentShouldRing) {
    shouldRing = false;
  }

  if (shouldRing) {
    if (ringPhase) {
      // We're in the phase where we ring, set the pin according to our state
      digitalWrite(forwardReversePin, isHigh ? HIGH : LOW);
      digitalWrite(ringModePin, HIGH);

      // Flip our state
      isHigh = !isHigh;

      // Determine if we should exit the ring phase
      if (++ringIterationCounter >= 20) {
        ringPhase = false;
        ringIterationCounter = 0;
      }
    }
    else {
      digitalWrite(forwardReversePin, LOW);
      digitalWrite(ringModePin, LOW);
      if (++ringIterationCounter >= 60) {
        ringPhase = true;
        ringIterationCounter = 0;
      }
    }
  }
  else {
    digitalWrite(forwardReversePin, LOW);
    digitalWrite(ringModePin, LOW);
  }
  delay(RING_DELAY);
}
