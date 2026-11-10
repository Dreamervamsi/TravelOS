import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Animated,
  Easing,
  Pressable,
  SafeAreaView,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Audio } from 'expo-av';

const API_BASE_URL = 'http://127.0.0.1:8000'; // Use your computer's LAN IP on a physical phone.
type Screen = 'home' | 'voice';
type VoiceStatus = 'starting' | 'listening' | 'sending' | 'stopped';

const trips = [
  { title: 'Kyoto Temple Walks', subtitle: 'Fushimi Inari, Gion alleys & tea ceremony moments.', place: 'JAPAN', colors: ['#EAA479', '#54433D', '#142F3A'] },
  { title: 'Amalfi Coast', subtitle: 'Sunlit villages, quiet coves & winding coastal roads.', place: 'ITALY', colors: ['#59B9C8', '#277E91', '#F2B37A'] },
  { title: 'Alpine Escape', subtitle: 'Mountain air, lake walks & postcard views.', place: 'SWITZERLAND', colors: ['#A6D3DC', '#427C8A', '#E5BD8C'] },
];

export default function App() {
  const [screen, setScreen] = useState<Screen>('home');
  const [status, setStatus] = useState<VoiceStatus>('starting');
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [error, setError] = useState('');
  const pulse = useRef(new Animated.Value(1)).current;
  const level = useRef(new Animated.Value(1)).current;
  const quietSince = useRef<number | null>(null);
  const heardSpeech = useRef(false);
  const closing = useRef(false);

  useEffect(() => {
    if (screen !== 'voice' || status === 'stopped' || status === 'sending') return;
    const animation = Animated.loop(Animated.sequence([
      Animated.timing(pulse, { toValue: status === 'listening' ? 1.055 : 1.025, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 1100, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
    ]));
    animation.start();
    return () => animation.stop();
  }, [screen, status, pulse]);

  useEffect(() => {
    if (screen === 'voice') startListening();
    return () => { void stopRecordingOnly(); };
    // Voice session begins once when the assistant screen opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [screen]);

  const startListening = async () => {
    try {
      setError('');
      setStatus('starting');
      const permission = await Audio.requestPermissionsAsync();
      if (!permission.granted) throw new Error('Microphone access is needed to ask a voice question.');
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true, staysActiveInBackground: false });
      const next = new Audio.Recording();
      await next.prepareToRecordAsync({
        ...Audio.RecordingOptionsPresets.HIGH_QUALITY,
        isMeteringEnabled: true,
      });
      next.setProgressUpdateInterval(250);
      next.setOnRecordingStatusUpdate((s) => {
        if (!s.isRecording || closing.current) return;
        const meter = s.metering ?? -160;
        const talking = meter > -42;
        if (talking) {
          heardSpeech.current = true;
          quietSince.current = null;
          setStatus('listening');
          Animated.timing(level, { toValue: 1.12, duration: 160, useNativeDriver: true }).start();
        } else {
          Animated.timing(level, { toValue: 0.94, duration: 380, useNativeDriver: true }).start();
          if (heardSpeech.current) {
            quietSince.current ??= Date.now();
            if (Date.now() - quietSince.current > 1600) void finishListening(next);
          }
        }
      });
      await next.startAsync();
      setRecording(next);
      setStatus('listening');
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Could not start the microphone.';
      setError(message);
      setStatus('stopped');
    }
  };

  const stopRecordingOnly = async () => {
    if (!recording) return;
    try {
      const s = await recording.getStatusAsync();
      if (s.isRecording) await recording.stopAndUnloadAsync();
    } catch { /* The recorder may already have been closed by the silence timer. */ }
  };

  const finishListening = async (active = recording) => {
    if (closing.current || !active) return;
    closing.current = true;
    setStatus('sending');
    try {
      await active.stopAndUnloadAsync();
      const uri = active.getURI();
      setRecording(null);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      if (uri) {
        const form = new FormData();
        form.append('file', { uri, name: 'voice-question.m4a', type: 'audio/m4a' } as unknown as Blob);
        const response = await fetch(`${API_BASE_URL}/api/transcribe`, { method: 'POST', body: form });
        if (!response.ok) throw new Error(`Transcription request failed (${response.status}).`);
      }
      setStatus('stopped');
      setTimeout(() => setScreen('home'), 450);
    } catch (e) {
      const message = e instanceof Error ? e.message : 'Could not send your voice question.';
      setError(message);
      setStatus('stopped');
    }
  };

  const openVoice = () => {
    closing.current = false;
    quietSince.current = null;
    heardSpeech.current = false;
    setScreen('voice');
  };

  if (screen === 'voice') {
    return (
      <SafeAreaView style={styles.voicePage}>
        <StatusBar barStyle="dark-content" />
        <Pressable accessibilityLabel="Close voice assistant" onPress={() => { closing.current = true; void stopRecordingOnly(); setScreen('home'); }} style={styles.voiceClose}>
          <Text style={styles.closeGlyph}>×</Text>
        </Pressable>
        <View style={styles.orbStage}>
          <Orb pulse={pulse} level={level} active={status === 'listening'} />
        </View>
        <View style={styles.voiceFooter}>
          <Text style={styles.voiceTitle}>{status === 'starting' ? 'Getting ready…' : status === 'sending' ? 'One moment…' : status === 'stopped' ? 'Voice session ended' : 'I’m listening'}</Text>
          <Text style={styles.voiceHint}>{error || (status === 'listening' ? 'Speak naturally. I’ll close when you’re done.' : 'Your voice is sent securely for transcription.')}</Text>
          {status === 'sending' && <ActivityIndicator color="#8D71F4" style={{ marginTop: 20 }} />}
          <Pressable style={styles.endButton} onPress={() => { closing.current = true; void stopRecordingOnly(); setScreen('home'); }}>
            <Text style={styles.endButtonText}>End voice session</Text>
          </Pressable>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.page}>
      <StatusBar barStyle="dark-content" />
      <ScrollView contentContainerStyle={styles.homeContent} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View><Text style={styles.eyebrow}>CURRENT LOCATION</Text><Text style={styles.location}>Netherlands <Text style={styles.chevron}>⌄</Text></Text></View>
          <View style={styles.avatar}><Text style={styles.avatarText}>W</Text></View>
        </View>
        <View style={styles.search}><Text style={styles.searchIcon}>⌕</Text><Text style={styles.searchText}>Search destinations, activities…</Text><Text style={styles.filterIcon}>☷</Text></View>
        <View style={styles.sectionHeading}><View><Text style={styles.eyebrow}>MAKE ROOM FOR WONDER</Text><Text style={styles.sectionTitle}>Select your next trip</Text></View><Text style={styles.seeAll}>See all</Text></View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
          {['🌏  Asia', '🌍  Europe', '🌎  America', '✦  All'].map((item, i) => <View key={item} style={[styles.chip, i === 0 && styles.activeChip]}><Text style={[styles.chipText, i === 0 && styles.activeChipText]}>{item}</Text></View>)}
        </ScrollView>
        <ScrollView horizontal pagingEnabled={false} showsHorizontalScrollIndicator={false} contentContainerStyle={styles.cards}>
          {trips.map((trip, i) => <View key={trip.title} style={[styles.tripCard, i > 0 && { marginLeft: 14 }]}>
            <View style={[styles.cardSky, { backgroundColor: trip.colors[0] }]}><View style={[styles.sun, { backgroundColor: i === 0 ? '#FFD19D' : '#FFF0C7' }]} /><View style={[styles.mountainBack, { borderBottomColor: trip.colors[1] }]} /><View style={[styles.mountainFront, { borderBottomColor: trip.colors[2] }]} /><View style={styles.cardPlace}><Text style={styles.cardPlaceText}>{trip.place}</Text></View></View>
            <View style={styles.cardShade} />
            <View style={styles.rating}><Text style={styles.star}>★</Text><Text style={styles.ratingText}>5.0</Text></View>
            <View style={styles.cardCopy}><Text style={styles.cardTitle}>{trip.title}</Text><Text style={styles.cardSubtitle}>{trip.subtitle}</Text></View>
            <Pressable onPress={openVoice} style={styles.cardArrow}><Text style={styles.arrowText}>↗</Text></Pressable>
          </View>)}
        </ScrollView>
        <View style={styles.sectionHeading}><View><Text style={styles.eyebrow}>CURATED FOR YOU</Text><Text style={styles.sectionTitle}>A little inspiration</Text></View></View>
        <View style={styles.inspiration}><Text style={styles.inspirationIcon}>✧</Text><View style={{ flex: 1 }}><Text style={styles.inspirationTitle}>Find your kind of getaway</Text><Text style={styles.inspirationText}>Slow mornings, new places, and a plan that feels like yours.</Text></View><Text style={styles.inspirationArrow}>›</Text></View>
      </ScrollView>
      <View style={styles.bottomBar}>
        <View style={styles.navActive}><Text style={styles.navGlyph}>⌂</Text><Text style={styles.navActiveText}>Home</Text></View>
        <Text style={styles.navGlyph}>♡</Text><Text style={styles.navGlyph}>▤</Text><Text style={styles.navGlyph}>♙</Text>
      </View>
      <Pressable accessibilityRole="button" onPress={openVoice} style={styles.askButton}>
        <Text style={styles.askOrb}>✦</Text><Text style={styles.askText}>Ask AI</Text><Text style={styles.askArrow}>↗</Text>
      </Pressable>
    </SafeAreaView>
  );
}

function Orb({ pulse, level, active }: { pulse: Animated.Value; level: Animated.Value; active: boolean }) {
  return <Animated.View style={[styles.orbWrap, { transform: [{ scale: Animated.multiply(pulse, level) }] }]}>
    <View style={[styles.orbHalo, active && styles.orbHaloActive]} />
    <View style={styles.orbRing} />
    <View style={styles.orbBody}>
      <View style={styles.orbBase} />
      <View style={[styles.colorCloud, styles.cloudBlue]} /><View style={[styles.colorCloud, styles.cloudPurple]} />
      <View style={[styles.colorCloud, styles.cloudPink]} /><View style={[styles.colorCloud, styles.cloudCyan]} />
      <View style={styles.orbGloss} /><View style={styles.orbCore} />
    </View>
  </Animated.View>;
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: '#F7F7F9' }, homeContent: { paddingHorizontal: 22, paddingTop: 15, paddingBottom: 130 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 },
  eyebrow: { color: '#9399A5', fontSize: 11, fontWeight: '700', letterSpacing: 1.05 }, location: { color: '#24262B', fontSize: 26, fontWeight: '700', marginTop: 5, letterSpacing: -0.7 }, chevron: { color: '#44474F', fontSize: 23 }, avatar: { width: 44, height: 44, backgroundColor: '#EEE6FF', borderRadius: 22, alignItems: 'center', justifyContent: 'center', borderWidth: 2, borderColor: '#FFF' }, avatarText: { color: '#7C60DB', fontWeight: '700', fontSize: 16 },
  search: { height: 58, borderRadius: 19, backgroundColor: '#FFF', borderColor: '#E7E6EB', borderWidth: 1, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 17, marginBottom: 31 }, searchIcon: { fontSize: 28, color: '#282A30', marginRight: 12 }, searchText: { color: '#969BA5', flex: 1, fontSize: 14 }, filterIcon: { fontSize: 23, color: '#45474D' },
  sectionHeading: { flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', marginBottom: 17 }, sectionTitle: { fontSize: 22, fontWeight: '700', color: '#27292E', marginTop: 5, letterSpacing: -0.5 }, seeAll: { color: '#8D71E9', fontWeight: '600', marginBottom: 3 },
  chips: { paddingBottom: 22, gap: 9 }, chip: { borderRadius: 22, borderWidth: 1, borderColor: '#E3E2E8', paddingHorizontal: 16, height: 42, justifyContent: 'center', backgroundColor: '#FFF' }, activeChip: { backgroundColor: '#EEC4F5', borderColor: '#EEC4F5' }, chipText: { fontSize: 13, color: '#464850', fontWeight: '500' }, activeChipText: { color: '#3E3446' },
  cards: { paddingBottom: 34, paddingRight: 22 }, tripCard: { width: 274, height: 372, borderRadius: 27, overflow: 'hidden', backgroundColor: '#274B57' }, cardSky: { ...StyleSheet.absoluteFillObject }, sun: { width: 92, height: 92, borderRadius: 50, position: 'absolute', top: 66, right: 41, opacity: 0.85 }, mountainBack: { position: 'absolute', bottom: 72, left: -10, width: 310, height: 195, borderLeftWidth: 155, borderRightWidth: 155, borderBottomWidth: 178, borderLeftColor: 'transparent', borderRightColor: 'transparent', opacity: 0.9 }, mountainFront: { position: 'absolute', bottom: 45, left: -22, width: 340, height: 155, borderLeftWidth: 170, borderRightWidth: 170, borderBottomWidth: 138, borderLeftColor: 'transparent', borderRightColor: 'transparent', opacity: 0.94 }, cardPlace: { position: 'absolute', top: 22, left: 20, paddingHorizontal: 11, paddingVertical: 7, borderRadius: 20, backgroundColor: 'rgba(255,255,255,0.22)' }, cardPlaceText: { fontSize: 10, color: '#FFF', fontWeight: '700', letterSpacing: 1.3 }, cardShade: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(10,18,26,0.18)' }, rating: { position: 'absolute', top: 19, right: 18, borderRadius: 18, paddingHorizontal: 10, height: 32, flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(28,30,34,0.45)', gap: 5 }, star: { color: '#F6C4FB', fontSize: 13 }, ratingText: { color: '#FFF', fontSize: 12, fontWeight: '600' }, cardCopy: { position: 'absolute', bottom: 23, left: 21, right: 65 }, cardTitle: { color: '#FFF', fontSize: 22, lineHeight: 26, fontWeight: '700' }, cardSubtitle: { color: 'rgba(255,255,255,.88)', fontSize: 12, lineHeight: 17, marginTop: 8 }, cardArrow: { width: 48, height: 48, borderRadius: 25, backgroundColor: '#F2C5F8', position: 'absolute', bottom: 22, right: 18, alignItems: 'center', justifyContent: 'center' }, arrowText: { color: '#292631', fontSize: 24 },
  inspiration: { flexDirection: 'row', alignItems: 'center', borderRadius: 20, padding: 17, backgroundColor: '#FFF', borderColor: '#ECEAF0', borderWidth: 1 }, inspirationIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: '#F4E4F8', color: '#A356B8', textAlign: 'center', textAlignVertical: 'center', fontSize: 24, marginRight: 12, overflow: 'hidden' }, inspirationTitle: { color: '#292B31', fontWeight: '700', fontSize: 14 }, inspirationText: { color: '#888D98', fontSize: 12, lineHeight: 17, marginTop: 4 }, inspirationArrow: { fontSize: 26, color: '#9B8BCB', marginLeft: 8 },
  bottomBar: { position: 'absolute', left: 22, right: 22, bottom: 17, height: 70, borderRadius: 35, backgroundColor: '#202326', flexDirection: 'row', justifyContent: 'space-around', alignItems: 'center', paddingHorizontal: 10 }, navActive: { height: 46, paddingHorizontal: 17, borderRadius: 24, backgroundColor: '#FFF', flexDirection: 'row', alignItems: 'center', gap: 7 }, navGlyph: { color: '#F8F8FA', fontSize: 23 }, navActiveText: { color: '#25272B', fontSize: 13, fontWeight: '600' },
  askButton: { position: 'absolute', right: 28, bottom: 103, height: 58, borderRadius: 30, paddingHorizontal: 17, flexDirection: 'row', alignItems: 'center', gap: 9, backgroundColor: '#FFF', borderWidth: 1, borderColor: '#E8D8F4', elevation: 5, shadowColor: '#81718D', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.16, shadowRadius: 12 }, askOrb: { fontSize: 18, color: '#9A73F0', textShadowColor: '#83D9FA', textShadowRadius: 7 }, askText: { color: '#24252A', fontWeight: '600', fontSize: 15 }, askArrow: { color: '#8870D7', fontSize: 18, marginLeft: 1 },
  voicePage: { flex: 1, backgroundColor: '#F6F7F9', alignItems: 'center' }, voiceClose: { position: 'absolute', top: 18, right: 22, width: 44, height: 44, borderRadius: 23, backgroundColor: '#FFF', borderWidth: 1, borderColor: '#E8E7EB', alignItems: 'center', justifyContent: 'center', zIndex: 2 }, closeGlyph: { fontSize: 27, color: '#42444A', lineHeight: 30 }, orbStage: { flex: 1, width: '100%', alignItems: 'center', justifyContent: 'center', paddingTop: 35 },
  orbWrap: { width: 304, height: 304, alignItems: 'center', justifyContent: 'center' }, orbHalo: { position: 'absolute', width: 300, height: 300, borderRadius: 150, backgroundColor: 'rgba(255,255,255,.64)', borderWidth: 1, borderColor: 'rgba(255,255,255,.9)', shadowColor: '#A0A2B4', shadowRadius: 30, shadowOpacity: 0.14, shadowOffset: { width: 0, height: 9 } }, orbHaloActive: { shadowColor: '#9E72F2', shadowOpacity: 0.32, shadowRadius: 34 }, orbRing: { position: 'absolute', width: 260, height: 260, borderRadius: 130, borderColor: 'rgba(209,185,255,.24)', borderWidth: 1 }, orbBody: { width: 226, height: 226, borderRadius: 112, overflow: 'hidden', backgroundColor: '#FAFAFF', alignItems: 'center', justifyContent: 'center', shadowColor: '#8879D2', shadowRadius: 17, shadowOpacity: 0.18, shadowOffset: { width: 0, height: 8 }, elevation: 8 }, orbBase: { ...StyleSheet.absoluteFillObject, backgroundColor: '#FAFBFF' }, colorCloud: { position: 'absolute', width: 150, height: 150, borderRadius: 85, opacity: 0.88 }, cloudBlue: { top: -23, left: -21, backgroundColor: '#4DBDFF', shadowColor: '#178DFF', shadowRadius: 27, shadowOpacity: 0.9 }, cloudPurple: { top: -18, right: -22, backgroundColor: '#9C4CF4', shadowColor: '#8246FF', shadowRadius: 25, shadowOpacity: 1 }, cloudPink: { bottom: -43, left: -12, backgroundColor: '#E59BFC', shadowColor: '#ED75D5', shadowRadius: 29, shadowOpacity: 0.9 }, cloudCyan: { bottom: -38, right: -31, backgroundColor: '#45DBEB', shadowColor: '#30DBE9', shadowRadius: 26, shadowOpacity: 0.85 }, orbGloss: { position: 'absolute', width: 104, height: 205, left: 53, top: 4, borderRadius: 55, backgroundColor: 'rgba(255,255,255,.58)', transform: [{ rotate: '30deg' }] }, orbCore: { position: 'absolute', width: 124, height: 126, borderRadius: 66, backgroundColor: 'rgba(250,251,255,.72)' },
  voiceFooter: { alignItems: 'center', width: '100%', paddingHorizontal: 32, paddingBottom: 38 }, voiceTitle: { fontSize: 25, fontWeight: '600', color: '#202126', letterSpacing: -0.5 }, voiceHint: { minHeight: 42, textAlign: 'center', color: '#8C919B', fontSize: 14, lineHeight: 20, marginTop: 9 }, endButton: { height: 54, minWidth: 210, marginTop: 17, borderRadius: 28, backgroundColor: '#F0D2F6', alignItems: 'center', justifyContent: 'center' }, endButtonText: { color: '#34313A', fontSize: 15, fontWeight: '600' },
});
