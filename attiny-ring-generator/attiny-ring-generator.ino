int inputPin = 1;
int forwardReversePin = 3;
int ringModePin = 4;
int ringDelay = 50; // 20Hz
int ringIteration = 0;

void setup() {
  pinMode(inputPin, INPUT);
  pinMode(forwardReversePin, OUTPUT);
  pinMode(ringModePin, OUTPUT);
}

void loop() {
  if (digitalRead(inputPin)) {

    if (ringIteration < 20) {
      digitalWrite(ringModePin, HIGH);
      digitalWrite(forwardReversePin, ringIteration % 2 == 0 ? HIGH : LOW);
    } else {
      digitalWrite(ringModePin, LOW);
    }

    if (ringIteration < 80) { // 20Hz * 4 seconds = 80 iterations
      ringIteration++;
    } else {
      ringIteration = 0;
    }
  }
  else {
    ringIteration = 0;
  }
  delay(ringDelay);
}
