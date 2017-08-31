<?php
    $devurl = "http://testing.shippingapis.com/ShippingAPITest.dll";
    $liveurl = "http://production.shippingapis.com/ShippingAPI.dll";
    
    $service = "RateV4";
    
    $longopts = array('origZip:', 'destZip:');
    $options = getopt('o:d:',$longopts);
    
    $xml = rawurlencode('<RateV4Request USERID="">
    $xml = rawurlencode('<RateV4Request USERID="">
                        <Revision>2</Revision>
                        <Package ID="1ST">
                        <Service>PRIORITY CPP</Service>
                        <ZipOrigination>'.$options['origZip'].'</ZipOrigination>
                        <ZipDestination>'.$options['destZip'].'</ZipDestination>
                        <Pounds>0</Pounds>
                        <Ounces>3.5</Ounces>
                        <Container/>
                        <Size>REGULAR</Size>
                        <Machinable>true</Machinable>
                        </Package>
                        </RateV4Request>');
                        
                        $request = $liveurl . "?API=" . $service . "&xml=" . $xml;
                        $session = curl_init();
                        
                        curl_setopt($session, CURLOPT_URL, $request);
                        curl_setopt($session, CURLOPT_HTTPGET, 1);
                        curl_setopt($session, CURLOPT_HEADER, false);
                        curl_setopt( $session , CURLOPT_SSL_VERIFYPEER , false );
                        curl_setopt( $session , CURLOPT_SSL_VERIFYHOST , false );
                        curl_setopt($session, CURLOPT_HTTPHEADER, array('Accept: application/xml', 'Content-Type: application/xml'));
                        curl_setopt($session, CURLOPT_RETURNTRANSFER, true);
                        
                        if(ereg("^(https)",$devurl)) curl_setopt($session,CURLOPT_SSL_VERIFYPEER,false);
                        $response = curl_exec($session);
                        curl_close($session); 
                        $xml = new SimpleXMLElement($response);
                        $rate = $xml->Package->Postage->Rate; 
                        echo '
                        Rate '.$rate;

