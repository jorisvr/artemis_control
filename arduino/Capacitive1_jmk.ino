#include <CapacitiveSensor.h>

/*
 * CapitiveSense Library Demo Sketch
 * Paul Badger 2008
 * Uses a high value resistor e.g. 10 megohm between send pin and receive pin
 * Resistor effects sensitivity, experiment with values, 50 kilohm - 50 megohm. Larger resistor values yield larger sensor values.
 * Receive pin is the sensor pin - try different amounts of foil/metal on this pin
 * Best results are obtained if sensor foil and wire is covered with an insulator such as paper or plastic sheet
 */


CapacitiveSensor   cs_8_9 = CapacitiveSensor(9,8);        // 10 megohm resistor between pins 8 & 9, pin 9 is sensor pin, add wire, foil

byte switchState = LOW;
byte oldSwitchState = LOW;
byte paused = LOW; // assume to game start unpaused
const unsigned long debounceTime = 1000;  // milliseconds


void setup()                    
{

   cs_8_9.set_CS_AutocaL_Millis(0xFFFFFFFF);     // turn off autocalibrate on channel 1 - just as an example
//   cs_8_9.set_CS_Timeout_Millis(5000); // default 2000
   Serial.begin(9600);

}

void loop()                    
{
    long start = millis();
    long total1 =  cs_8_9.capacitiveSensor(10);

//    Serial.print(millis() - start);        // check on performance in milliseconds
//    Serial.print("\t");                    // tab character for debug window spacing
//    Serial.print(total1);                  // print sensor output 1

    // has it changed since last time?
   if (total1 > 50000) // capitance value, different for each button
   {
    switchState=HIGH;
   }
   else
   {
    switchState=LOW;
   }
//   Serial.println(switchState);
   if (switchState != oldSwitchState)
    {
    oldSwitchState =  switchState;  // remember for next time 
    digitalWrite(LED_BUILTIN, HIGH);
    delay (debounceTime);   // debounce
    digitalWrite(LED_BUILTIN, LOW); // show buttonpress is detected by led
    if (switchState == HIGH)
       {
//                 Serial.println ("pause"); // simple serial "pause"
//       Serial.println ("Switch being pushed");
       if (paused == LOW) // detect if paused then start
          {
          Serial.println ("pause");
          paused = HIGH;
          }
       else
          {
          Serial.println ("start");
          paused = LOW;
          }   
       }  // end if switchState is LOW
    else
       {
//       Serial.println ("Switch letting go");
       }  // end if switchState is HIGH
    }  // end of state change

    delay(10);                             // arbitrary delay to limit data to serial port 
}

