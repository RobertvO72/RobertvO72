# Start automatisch dmv crontab  (edit dmv sudo crontab -e)
#  				daar staat in:       @reboot sudo python /robert/zonstuur.py &  (& zorgt dat hij doorgaat zonder dat deze eerst hoeft af te ronden, daar dit niet gebeurt)

import time, csv, pickle
import urllib2, json, base64, urllib
from urllib import urlencode # new module and function
import RPi.GPIO as GPIO
import os
import logging # for logging
GPIO.setmode(GPIO.BCM)


GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(24, GPIO.OUT)
GPIO.setup(10, GPIO.OUT)
GPIO.setup(9, GPIO.OUT)
GPIO.setup(25, GPIO.OUT)
GPIO.setup(11, GPIO.OUT)
GPIO.setup(8, GPIO.IN)
GPIO.setup(7, GPIO.IN)

GPIO.output(27, False)
GPIO.output(22, False)
GPIO.output(23, False)
GPIO.output(24, False)
GPIO.output(10, False)
GPIO.output(9, False)
GPIO.output(25, False) # uitgang watchdog
GPIO.output(11, False)




def temperaturen(sensor_Raw):
    sensorids = ["28-0000054c4932", "28-0004314271ff", "28-0000054c9fca", "28-0000054c4401", "28-0000054dab99", 
		 "28-0000054cf9b4", "28-0000054c8a03", "28-0000054d6780", "28-0000054ccdfa", "28-0000054c4f9d"]
    # benaming   vat bovenop =0   - vat bovenin =1   - vat onder =2     - Zonnecollector =3- WW Haard =4      - CV voor WW =5    
	# - CV na WW =6 - huiskamer =7 - buitentemp =8 - reserve =9 (verbrande sensor haard =28-0000054c9454
    for sensor in range (len(sensorids)):
            temperatures = "-5" # voor als hij niets meet
            text = ''
            while text.split("\n")[0].find("YES") == -1:
                try:
                    tfile = open("/sys/bus/w1/devices/"+ sensorids[sensor] +"/w1_slave")
                except:
                    temperatures == "-100"
                    break
                else:
                    text = tfile.read()
                    tfile.close()
                    secondline = text.split("\n")[1]
                    temperaturedata = secondline.split(" ")[9]
                    temperature = float(temperaturedata [2:])
                    temperatures = (temperature / 1000)
                    temperatures = ("%.1f" % round(temperatures,1))
                    break
            else:
                    print("CRC niet correct")
            sensor_Raw[sensor] = temperatures

    # temperaturen overrulen voor test
    # sensor_Raw[0] = float(raw_input("Voer S0 in "))
    # sensor_Raw[1] = float(raw_input("Voer S1 in "))
    # sensor_Raw[2] = float(raw_input("Voer S2 in "))
    # sensor_Raw[0] = 85
    # sensor_Raw[3] = float(raw_input("Voer S3 in "))
    # sensor_Raw[4] = float(sensor_Raw[4]) - float(5)			 #correctie erop
    # sensor_Raw[5] = 30
    # sensor_Raw[6] = 30
    # sensor_Raw[7] = 30
    # sensor_Raw[8] = 30
    # sensor_Raw[9] = 30

    return sensor_Raw

def insert(sensor_Raw):

    username = 'username'
    password = 'password'

    data = (sensor_Raw) 
    # print data
    bulkData = json.dumps(data, ensure_ascii = 'False')
    postData = urllib.urlencode({'results':bulkData})
    try:    
        # request = urllib2.Request("http://www.webermontage.nl/Zonneboiler/insert.php")
	request = urllib2.Request("http://www.fam-vanommen.nl/zonneboiler/insert.php")

        base64string = base64.encodestring('%s:%s' % (username, password)).replace('\n', '')
        request.add_header("Authorization", "Basic %s" % base64string)
        result = urllib2.urlopen(request, postData) # encoded_data)
        # result is of storing (< 5 tekens) of wijziging parameters > 5 tekens
        para = []
        raw_text = result.read()
        if len(raw_text) > 5: # Dus er zijn gewijzigde parameters teruggestuurd

            text_array = raw_text.split(',')
            for item in text_array:
                para.append(item)
            
            sensor_Raw[15] = para[0]
            print para[0] # REGELING
            sensor_Raw[16] = para[1]
            print para[1] # VLVERWL
            sensor_Raw[18] = para[2]
            print para[2] # VLOERVRAAG
            sensor_Raw[20] = para[3]
            print para[3] # TIJDVLOER
            sensor_Raw[25] = para[4]
            print para[4] # SETPOINT WOONKAMER BIJV. TBV VERWARMING OP GAS
            sensor_Raw[27] = para[5]
            print para[5] # VERWARMING OP GAS
            
            pickle.dump(para, open( "/robert/parameters.dump", "w" ))

        # else:

    except :
        pass
    
#####  HIER BEGINT HET PROGRAMMA
try: # (wanneer deze try fout is (bijv. door ctrl C, worden de GPIO's gecleanup 't, 03-04-18 exeption toegevoegd voor doorgaan bij fouten)


    sensor_Raw = {}
    # Lees deze variabelen bij opstarten van SD kaart uit parameters.dump, als deze bestaat.
    try:
        para =  pickle.load( open( "/robert/parameters.dump", 'r+b' ))
        sensor_Raw[15] = para[0] # REGELING
        sensor_Raw[16] = para[1] # VLVERWL
        sensor_Raw[18] = para[2] # VLOERVRAAG
        sensor_Raw[20] = para[3] # TIJDVLOER
        sensor_Raw[25] = para[4] # SETPOINT
        sensor_Raw[27] = para[5] # VERWARMING VRAAG OP GAS

    except:
        sensor_Raw[15] = "J" # REGELING
        sensor_Raw[16] = "J" # VLVERWL
        sensor_Raw[18] = "N" # VLOERVRAAG
        sensor_Raw[20] = 0   # TIJDVLOER
        sensor_Raw[25] = 0   # SETPOINT
        sensor_Raw[27] = "N" # VERWARMING VRAAG OP GAS






    t0 = time.time()
    memTemp = 0
    memTempcount = 0
    voorkeurTemp = 0
    klep_ZonHaard = 0
    pomp = 0
    klep_Ww = 0
    vatTemp = 80
    reseT200 = 0
    vlverwVraag = 0
    staTus = 0
    state = 0
    sensor_Raw[18] = "N"
    sensor_Raw[14] = "N" # KETEL
    sensor_Raw[27] = "N" # VERWARMINGSVRAAG
    sensor_Raw[13] = 0   # pompsnelheid
    while True:
        temperaturen(sensor_Raw)
    
        # sensor_Raw[10]="N" # KLEPBRON
        # sensor_Raw[11]="J" # KLEPWW
        # sensor_Raw[12]="N" # KLEPNAVERW
        # sensor_Raw[13]=30  # POMP
        # sensor_Raw[14]="N" # KETEL
        # ssensor_Raw[15]="J" # REGELING
        # sensor_Raw[16]="N" # VLVERWL
        sensor_Raw[17]="N" # VLVERWH
        # sensor_Raw[18]="N" # VLOERVRAAG
        # sensor_Raw[19]="N" # VLVERWACTIEF
        # sensor_Raw[20]=40  # TIJDVLOER
        # sensor_Raw[21]=30  # TIJDOVER
        if ( GPIO.input(8) == False ):
            sensor_Raw[22]="J" # HAARD
        else:
            sensor_Raw[22]="N" # HAARD
        if ( GPIO.input(7) == False ):
            sensor_Raw[23]="J" # DOUCHE
        else:
            sensor_Raw[23]="N" # DOUCHE
        # sensor_Raw[23]="N" # DOUCHE
        sensor_Raw[24]="NOT YET" # STORING
        # sensor_Raw[25]=20  # SETPOINT
        # sensor_Raw[26]="N" # WIJZIGING, OM AAN TE GEVEN OF ER PARAMETERS GEWIJZIGD ZIJN DOOR WEBSITE, EN DUS TERUG GESCHREVEN MOETEN WORDEN IN PYTHON
        # sensor_Raw[27]="N" # VERWARMING, OM AAN TE GEVEN OF KETEL GESTUURD MOET WORDEN AFHANKELIJK VAN SETPOINT


        t1 = time.time()
        if t1 > t0 + 60: # 60 seconden
            insert(sensor_Raw)
            t0 = t0 + 60

	    # tbv hardware watchdog
            if sensor_Raw[0] <> sensor_Raw[1]:
		#print "ongelijk"
		GPIO.output(25, True)
            	time.sleep(.1)
            	GPIO.output(25, False)
    


    # Logica:

        S0 = float(sensor_Raw[0]) # Zonnecollector
        S1 = float(sensor_Raw[1]) # WW Haard
        S2 = float(sensor_Raw[2]) # Vat Bovenin
        S3 = float(sensor_Raw[3]) # Vat Bovenop
        S4 = float(sensor_Raw[4]) # Vat Onder
        S5 = float(sensor_Raw[5]) # CV voor WW
        S6 = float(sensor_Raw[6]) # CN na WW
        S7 = float(sensor_Raw[7]) # Huiskamer
        S8 = float(sensor_Raw[8]) # Buitentemperatuur
        S9 = float(sensor_Raw[9]) # Reserve
        SP = float(sensor_Raw[25]) # Setpoint Verwarming

	# soms fout dat alle temperaturen 200 graden worden en daarin blijven hangen
	
	# if S0 == 200 and S1 == 200 and S2 == 200 and S3 == 200 and S4 == 200:
	# 	print"fout in de sensoren, alle 200"
	#	reseT200 = reseT200 + 1
	#if reseT200 == 2000:
	#	# resetten
	#	os.system("reboot")
	#	quit()

        if S0  > 115:
            print "STALL"
            pomp = 0 # pomp uit

        else:
            # Eerst bepalen welke WW in het vat gekozen wordt.
            if S2 > 67:      # voeler boveninvat groter als 80, switch naar onder
		             # GPIO.output(10, True)
                klep_Ww = 1
                	     # sensor_Raw[11]="J" # KLEPWW
                 	     # vatTemp = S4
            elif S2 < 55:    # voeler boveninvat kleiner als 75, switch naar boven
                	     # GPIO.output(10, False)
                klep_Ww = 0
                # sensor_Raw[11]="N" # KLEPWW
                # vatTemp = S2
	    else:
		if vatTemp == 80:
			 vatTemp = S2 # Anders blijft vattemp tijdens start op 80 staan
	    
	    if klep_Ww == 1:
		vatTemp = S4
	    else:
		vatTemp = S2


	    # Dan bepalen waar de warmte vandaan komt. Zon of haard. Bij dalende temperaturen wordt deze regeling uitgeschakeld. Daarom eerst bepalen of temp. stijgt



            if S0 > S1 + 1 and S0 > vatTemp + 10 or S0 > 90:  # Voeler Zonnecollector > voeler WW Haard plus een graad diff  EN Voeler Zonnecollector > inhoud 'vatTemp' + 10 graad diff
                                                         # Of als voeler Zonnecollector > 90

                klep_ZonHaard = 1                        # klep naar Zonnecollector 

            if S1 - 1 > S0 or S0 < vatTemp -5:                # Voeler Haard > voeler Zonneboiler een graad diff
							 # Of als als zonnecolector < 'vatTemp' (omdat anders de collector het vat afkoelt)

                klep_ZonHaard = 0           		 # klep naar ww haard 


            if klep_ZonHaard == 1: 			 # Warmte van zon
                voorkeurTemp = S0 - 5			 # Deze op 18-7-15 van S0 - 5 naar S0 - 1 gezet 

            if klep_ZonHaard == 0:			 # Warmte van Haard
                voorkeurTemp = S1 - 9

            # Bepalen of voorkeurtemp zakt, dan pompsnelheid verlagen.        ///////////     Alleen wanneer onderkant vat geselecteerd. Anders onstabiel
            # Als 100x de temperatuur lager is als de vorige keer, pomp uit.
	    # 13-3-16 van 50 naar 100 gezet als test
	    # if klep_Ww == 1:
	    if memTemp >= voorkeurTemp :
		memTempcount = memTempcount + 1

	    if memTemp < voorkeurTemp :
		memTempcount = 0

	    if memTempcount == 200:
		pomp = 0
		memTempcount = 0

	    memTemp = voorkeurTemp



	    if memTempcount < 200:
            # pompsnelheid bepalen
		 if t1 > t0 + 30: # mbv deze 30 elke minuut opnieuw pompsnelheid bepalen 13-03-16

		         if pomp == 3:
		                if voorkeurTemp < vatTemp + 5:
		                    pomp = 2
		         elif pomp == 2:
		                if voorkeurTemp < vatTemp + 3:
		                    pomp = 1
		                elif voorkeurTemp > vatTemp + 8:
		                    pomp = 3
		         elif pomp == 1:
		                if klep_ZonHaard == 1: 
				  	if voorkeurTemp < vatTemp -2:  # op 18-07-15 -2 toegevoegd. Stond op 0
		                    		pomp = 0
		                	elif voorkeurTemp > vatTemp + 5:
		                    		pomp = 2
			 	else:
                                        if voorkeurTemp < vatTemp -10:  # op 18-07-15 -2 toegevoegd. Stond op 0
                                                pomp = 0
                                        elif voorkeurTemp > vatTemp + 5:
                                                pomp = 2

		         elif pomp == 0:
		                if voorkeurTemp > vatTemp + 2:
		                    pomp = 1

		 # if pomp > 1:   # ff testen pompsnelheid begrenzen 01-04-18 (helaas, pomp ging veel te laat uit
		 # 	 pomp = 1

	# if op ww haard max pompsnelheid is 1 03-12-17 
        # if klep_ZonHaard == 0:		# warmte van haard    
	#    if pomp == 3: # or pomp == 3:	
	#        pomp = 2
		


     
        # Bepalen klep naverwarming
        if S3 > 62:
            GPIO.output(9, False)
            sensor_Raw[12]="N" # KLEPNAVERW
	    staTus = 0
        elif S3 < 50:
            GPIO.output(9, True)
            sensor_Raw[12]="J" # KLEPNAVERW
    	    staTus = 1

        # Bepalen of en hoe lang vloerverwarming op WW haard draait en of warmte uit vat hierbij verbruikt wordt
        if vlverwVraag == 0:
            sensor_Raw[19] = "N"
            t11 = time.time() 
            t10 = time.time() 
            if sensor_Raw[18] == "J":
                sensor_Raw[19] = "J"
                t10 = time.time()
	        t11 = time.time()
                vlverwVraag = 1
                GPIO.output(11, True) # pomp WW + pomp ketel aan

	elif vlverwVraag == 1:
            t11 = time.time()
            sensor_Raw[19] = "J"
 
            # pomp aansturen. Dit om bovenste WW in schoorsteen te koelen
	    if pomp == 0:
		# pomp = 1
                klep_ZonHaard = 0   # klep naar ww haard
		if  sensor_Raw[16] == "J":	 # J = extra warmte uit vat halen VLVERWL Bovenin of onderin vat selecteren. Warmte uit vat naar vloer
			klep_Ww = 1
			pomp = 1
		else:
			klep_Ww = 0
			pomp = 1
			if t11 > t10 + 30: # na 30sec pomp uit
				pomp = 0
			if t11 > t10 + 90: # na 60 sec pomp weer aan
				t10 = time.time()

            if t11 > t10 + (60 * float(sensor_Raw[20])):
                vlverwVraag = 0
                GPIO.output(11, False)
                sensor_Raw[18] = "N"
            else:
                sensor_Raw[21] = float(sensor_Raw[20]) - ((t11 - t10)/60) # sensor_Raw[20] #  - str(t10)

            if sensor_Raw[18] == "N":  # wanneer door gebruiker regeling uitgezet wordt, uitschakelen
                GPIO.output(11, False) # pomp ww + pomp ketel uit
                vlverwVraag = 0
                sensor_Raw[21] = 0



        # Bepalen of de gewone verwarmingsketel moet gaan branden
  #      if sensor_Raw[27] == "J":
  #          if SP > S7:
  #              GPIO.output(25, True)
  #              sensor_Raw[14] = "J"
  #          elif SP < S7 - 1:
  #              GPIO.output(25, False)
  #              sensor_Raw[14] = "N"
  #      if sensor_Raw[27] == "N":
  #           GPIO.output(25, False)
  #           sensor_Raw[14] = "N"


        print "S0 =", S0
        print "S1 =", S1
        print "S2 =", S2
        print "S3 =", S3
        print "S4 =", S4
        print "S5 =", S5
        print "S6 =", S6
        print "S7 =", S7
        print "S8 =", S8
        print "S9 =", S9

#        print sensor_Raw[25]
#        print S7 - 1
#        print vlverwVraag
        print "Klep Zon=1-Haard=0 =", klep_ZonHaard
        print "Klep ww boven=0 onder=1 =", klep_Ww
	print "Klep naverw aan=0 uit=1 =",  staTus
        print "VatTemperatuur", vatTemp
        # print "Klep naverw =",sensor_Raw[12] # KLEPNAVERW
        print "Voorkeurtemp =", voorkeurTemp
        print "pompsnelheid =", sensor_Raw[13], " procent"
	print "Memtemp", memTemp
	print "memTempcount =", memTempcount
	print t0
	print t1
	print ""
	print ""

	#logging.basicConfig(filename='log.log',level=logging.DEBUG)
	#logging.basicConfig(filename='log.log',level=logging.DEBUG,format='%(asctime)s        %(message)s',datefmt='%m/%d/%y %I:%M:%S %P')
	log = 0
	if log == 1:
		LOG_LEVEL = logging.INFO
		LOG_FILE="/robert/log.log"
		LOG_FORMAT = "%(asctime)s %(levelname)s        %(message)s"
		logging.basicConfig(filename=LOG_FILE, format=LOG_FORMAT, level=LOG_LEVEL)

		logging.info('S0 = zoncollector:')
		logging.info(S0)
		logging.info('S1 = ww haard')
        	logging.info(S1)
        	logging.info('S2 = vat bovenin')
		logging.info(S2)
		logging.info('S3 = vat uittrede')
        	logging.info(S3)
		logging.info('S4 = vat onderin')
        	logging.info(S4)
		logging.info('S5 = CV voor WW')
	        logging.info(S5)
	        logging.info('S6 = CV na WW')
	        logging.info(S6)
	        logging.info('S7 = huiskamer')
	        logging.info(S7)
	        logging.info('S8 = buitentemp')
	        logging.info(S8)
	        logging.info('S9 = reserve (boilerroom)')
	        logging.info(S9)
		logging.info('klep_ZonHaard')
	        logging.info(klep_ZonHaard)
		logging.info('klep_ww')
	        logging.debug(klep_Ww)
		logging.info('status klep naverwarming, 1 is aan, 0 is uit')
	        logging.info(staTus)
		logging.info('Vattemp is S4 of S2, afhankelijk welke WW gekozen is')
	        logging.info(vatTemp)
		logging.info('Voorkeurtemp: Als warmte van zon: S0-5; Als warmte van haard S1-9')
	        logging.info(voorkeurTemp)
		logging.info('pompsnelheid (%)')
	        logging.info(sensor_Raw[13])
		logging.info('memtemp  memtemperatuur is om memtempcounter te laten tellen if >= voorkeurtemp memtempcount+1')
	        logging.info(memTemp)
		logging.info('memtempcount')
	        logging.info(memTempcount)
		logging.info('t0')
		logging.info (t0)
		logging.info('t1')
		logging.info(t1)

	        logging.info("")
	        logging.info("")

	if sensor_Raw[15] <> "J" and sensor_Raw[15] <> "N": # soms onverklaarbaar veld leeg en dus regeling uit
	   sensor_Raw[15] = "J"

        if  sensor_Raw[15] == "J": # REGELING AAN
           if pomp == 0:
               GPIO.output(27, False)
               GPIO.output(22, False)
               GPIO.output(23, False)
               sensor_Raw[13] = 0

           elif pomp == 1:
               GPIO.output(27, True)
               GPIO.output(22, False)
               GPIO.output(23, False)
               sensor_Raw[13] = 33

           elif pomp == 2:
               GPIO.output(27, True)
               GPIO.output(22, True)
               GPIO.output(23, False)
               sensor_Raw[13] = 66

           elif pomp == 3:
               GPIO.output(27, True)
               GPIO.output(22, True)
               GPIO.output(23, True)
               sensor_Raw[13] = 100

           if klep_ZonHaard == 0:
                GPIO.output(24, False)
                sensor_Raw[10]="N"

           elif klep_ZonHaard == 1:
                GPIO.output(24, True)
                sensor_Raw[10]="J"


           if klep_Ww == 0:
                GPIO.output(10, False)
                sensor_Raw[11]="N" # KLEPWW
           elif klep_Ww == 1:
                GPIO.output(10, True)
                sensor_Raw[11]="J" # KLEPWW

	   # Watchdog uitgang

	   # if (state == 1):
	   #	state = 0
	   # else:
	#	state = 1

	 #  if (state == 1):
# 	   GPIO.output(25, True)
#	   time.sleep(1)
#	   GPIO.output(25, False)

	  	
	   # if GPIO.output(25, False)
	   # if ( GPIO.output(25) == False ):
	   #	GPIO.output(25, True)

	   # else: GPIO.output(25, False)





        else:  # REGELING UIT
               GPIO.output(27, False) # pomps.1 uit
               GPIO.output(22, False) # pomps.2 uit
               GPIO.output(23, False) # pomps.3 uit
              

               GPIO.output(24, False) # klep zon/haard uit
               GPIO.output(10, False) # klep WW uit

               sensor_Raw[13] = 0     # Weergeven dat de pomp uitstaat


except:
    print("Except hit")
    logging.debug("Except hit")


finally:
    GPIO.cleanup() # this ensures a clean exit




# 0 = S0 (Temp zonnecollector)
# 1 = S1 (Temp WW Haard)
# 2 = S2 (Temp boven in vat)
# 3 = S3 (Temp uittrede vat)
# 4 = S4 (Temp onderin vat)
# 5 = S5 (Temp CV voor WW vlverw.)
# 6 = S6 (Temp CV na WW vlverw.)
# 7 = S7 (Temp Huiskamer)
# 8 = S8 (Temp Buiten)
# 9 = S9 (reserve)
#10 = KLEPBRON J/N
#11 = KLEPWW J/N
#12 = KLEPNAVERW J/N
#13 = POMP 33 / 66 / 100
#14 = KETEL J/N
#15 = REGELING J/N
#16 = VLVERWL J/N
#17 = VLVERWH (RESERVE)
#18 = VLOERVRAAG J/N
#19 = VLVERWACTIEF J/N
#20 = TIJDVLOER TIJD VAN 10 TOT 100 MIN
#21 = TIJDOVER TIJD
#22 = HAARD J/N
#23 = DOUCHE J/N
#24 = STORING TEXT
#25 = SETPOINT
#26 = WIJZIGING
#27 = VERWARMING
