//#include <AltSoftSerial.h>
//AltSoftSerial myserial;
// AltSoftSerial always uses these pins:
//
// Board          Transmit  Receive   PWM Unusable
// -----          --------  -------   ------------
// Teensy 3.0 & 3.1  21        20         22
// Teensy 2.0         9        10       (none)
// Teensy++ 2.0      25         4       26, 27
// Arduino Uno        9         8         10
// Arduino Leonardo   5        13       (none)
// Linkit 7688 Duo    5        13       (none)
// Arduino Mega      46        48       44, 45
// Wiring-S           5         6          4
// Sanguino          13        14         12

#include <SoftwareSerial.h>
#define RXPIN 8
#define TXPIN 9
SoftwareSerial myserial(RXPIN,TXPIN);

#define LCD_DISPLAY 0  //是否要啟用LCD顯示? (SDA ->A4, SDL->A5)
#define NORMAL_TAG_HEX_LENGTH 22  //正常的TAG, HEX格式轉成String的長度, 例如44-16-1-ed-ac-3c-d-e-30-0-e2-0-81-81-81-6-2-55-13-30-91-b 為 22
#define maxDelayTimeSameTag 30000  //幾秒內重複的內容就忽略
#define debugOutput 0
#define delayTime_after 60
#define delayTime_before 15

//-->  Command: Inventory 
//-->     [0] [1]   [2]     [3]           [4]   [5]   [6~ ]
//-->    固定 長度  幾筆TAG EPC長度(byte) 保留  保留  TAG_ID___________________________
//-->     32    12    1      e               30     0  e2 0 81 81 81 6 2 55 13 40 91 c 
char command_scantag[]={ 0x43,0x04,0x01,0xcd };
char command_scantag_next[]={ 0x31,0x03,0x02 }; 

//-->  Command: Inventory with RSSI 
//-->     [0] [1]   [2]     [3]           [4]   [5]   [6~ ]
//-->    固定 長度  幾筆TAG RSSI TAG_Frequency  EPC長度(byte)   保留  保留  TAG_ID_________________________________
//-->     44    16    1       9d  fc 37 d           e             30    0   e2 0 81 81 81 6 2 55 13 40 91 c 
char command_inventorytag[]={ 0x43,0x03,0x01 };  
char command_inventorytag_next[]={ 0x43,0x03,0x02 };  

//-->  Command: Select or Isolate Tag
//char command_findtag[]={ 0x33, 0x0F, 0x0C, 0xe2, 0x00, 0x81, 0x81, 0x81, 0x06, 0x02, 0x55, 0x13, 0x40, 0x91, 0x0c, 0x00, 0x00, 0x00, 0x00 };  
char command_findtag[]={  0x33, 0x0F, 0x0C, 0xe2, 0x00, 0x40, 0x00, 0x83, 0x12, 0x02, 0x16, 0x10, 0x10, 0xb2, 0x05 };  
//char command_findtag[]={  0x33, 0x0F, 0x0C, 0xe2, 0x0, 0x40, 0x0, 0x83, 0x12, 0x2, 0x16, 0x10, 0x10, 0xb2, 0x5  };  

//-->  Command: Read from Tag 
//-->     [0] [1]   [2]     [3]           [4]   [5]   [6~ ]
//-->    固定 長度  幾筆TAG RSSI TAG_Frequency  EPC長度(byte)   保留  保留  TAG_ID_________________________________
//-->     44    16    1       9d  fc 37 d           e             30    0   e2 0 81 81 81 6 2 55 13 40 91 c 
char command_readtag[]={ 0x37, 0x05, 0x01, 0x02, 0x06 };  

//-->  write to tags
//char command_scantag[]={ 0x35, 0x15, 0x01, 0x02, 0x00, 0x00, 0x00, 0x00, 0x06, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x10, 0x11, 0x12 };  
//Find a tag
//char command_scantag[]={ 0x33, 0x0F, 0x0C, 0x30, 0x08, 0x33, 0xb2, 0xdd, 0xd9, 0x01, 0x40  };  

byte incomingByte;
unsigned long lastScanTime = millis();
String lastScan;
String rfidGet;

#if defined(LCD_DISPLAY)
  #include <Wire.h> 
  #include <LiquidCrystal_I2C.h>
  LiquidCrystal_I2C lcd(0x27,20,4);  //set the LCD address to 0x27 for a 16 chars and 2 line display
#endif

void displayLCD(int yPosition, String txtMSG) {
  int xPos;
   if(txtMSG.length()>16) {
     xPos = 0;
     if(xPos<0) xPos=0;    
   }else{
      xPos = (16-txtMSG.length())/2;
   }
   lcd.setCursor(xPos,yPosition);
   lcd.print(txtMSG);
}

String padString(String stringTXT, char padTXT, int limitWidth,String alignType) {
  int numEmpty = limitWidth - stringTXT.length();
  for (int numI = 0; numI < numEmpty; numI++) {
    if(alignType=="left") {
      stringTXT = stringTXT + padTXT;
    }else if(alignType=="right") {
      stringTXT = padTXT + stringTXT;
    }else{
      (numI % 2 == 0) ? (stringTXT = padTXT + stringTXT) : (stringTXT = stringTXT + padTXT);
    }
  }
  return stringTXT;
}

void writeTAG() {
  myserial.print(command_scantag);
  delay(5);
  myserial.print(command_findtag);
}

String getValue(String data, char separator, int index)
{
  int found = 0;
  int strIndex[] = {0, -1};
  int maxIndex = data.length()-1;

  for(int i=0; i<=maxIndex && found<=index; i++){
    if(data.charAt(i)==separator || i==maxIndex){
        found++;
        strIndex[0] = strIndex[1]+1;
        strIndex[1] = (i == maxIndex) ? i+1 : i;
    }
  }

  return found>index ? data.substring(strIndex[0], strIndex[1]) : "";
}

boolean compareTag(String tag1, String tag2) {
  boolean rtnValue = 0;
  boolean tmpValue = 1;
  if(tag1.length()>NORMAL_TAG_HEX_LENGTH && tag2.length()>NORMAL_TAG_HEX_LENGTH) {
    if(tag1.length() == tag2.length()) {
      for(int i=6; i<NORMAL_TAG_HEX_LENGTH; i++){
        if(getValue(tag1, '-', i) != getValue(tag2, '-', i)) tmpValue = 0; 
      }

      if(tmpValue==0) {
        rtnValue = 0;
      }else{
        rtnValue = 1;
      }
    }
    
    
    return rtnValue;   
  }

  return rtnValue;
}

void readSerialOut() {  
    
    String rfidGetString;
    unsigned int i = 0; 
    boolean submitData = 0;

    if(myserial.available()) {
      lastScan = rfidGet;
      rfidGet = "";
      while (myserial.available())
      {   
        incomingByte = myserial.read();
        rfidGetString.concat(char(incomingByte)); // for String type
        if(i>0) rfidGet.concat('-');  // for HEX type    
        rfidGet.concat( String(incomingByte, HEX) );  // for HEX type  
        i++;
      }
    }

    if(debugOutput==1) {
      Serial.print("lastScan --> "); Serial.println(lastScan); 
      Serial.print("nowScan --> "); Serial.println(rfidGet);
      //Serial.print("i --> "); Serial.println(i);
    }
      
    
    if(i>=NORMAL_TAG_HEX_LENGTH) {
      /*
      //Serial.println("i>=NORMAL_TAG_HEX_LENGTH ");
      
      if(compareTag(lastScan,rfidGet)==0) {  // last tag and this tag are different
        if(debugOutput==1) Serial.println("Different tag.");
        submitData = 1;
      }else{
        if(millis()-lastScanTime>maxDelayTimeSameTag) {
          if(debugOutput==1) Serial.println("Same tag, but this tag not seen for a period.");
          submitData = 1;
        }else{
          if(debugOutput==1) Serial.println("Same tag, but has to wait.");        
        }
      }
    */
    submitData = 1;
    
      if(submitData==1) {
        if(debugOutput==1) {
          Serial.print(" TAG numbers: ");Serial.print(getValue(rfidGet,'-',2)); Serial.print("---> ");
        }
        Serial.print(" TAG:"); Serial.println(rfidGet);
        
        lastScanTime = millis();
        if(LCD_DISPLAY==1) {
          displayLCD(0, "                    ");
          displayLCD(1, "                    ");
          displayLCD(2, "                    ");
          displayLCD(3, "                    ");
        
        //unsigned int rfidLength = rfidGet.length();
        //unsigned int lines = rfidLength/20;
        displayLCD(0, rfidGet);
        //lcd.clear();
        }
      }        
    }else{
      Serial.println(rfidGet);
      rfidGet = lastScan;
      
    }
    if(debugOutput==1) Serial.println("--------------------------------------------------------------------------------------");
}

void setup()
{
  Serial.begin(9600);
  myserial.begin(9600);
  

  if(LCD_DISPLAY==1) {
    lcd.begin();
    lcd.backlight();
    displayLCD(0, "SunplusIT RFID");
    displayLCD(1, "Press R to scan");
  }  
}


boolean i = true;

void loop() {

  //Serial.println(i);
  
  if(myserial.available()) {
    readSerialOut();
    delay(delayTime_before);
  }else{ 
    
    myserial.print(command_scantag);
    delay(delayTime_after);
    /*
    if(i == true) {
      myserial.print(command_scantag);
      i = false;
    }else{
      myserial.print(command_scantag_next);
      i = true;
    }
    delay(delayTime_after);
    */
  }
  

}
