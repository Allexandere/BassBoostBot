from random import randint
from pydub import AudioSegment
from numpy import mean, std
import requests, vk, wget, os, json, math, threading


def main():

    VK_API_ACCESS_TOKEN = '4d8d7b04b056473c9b33d7fdffdc9795ba1c36856510942cb664aab6c6bce6255936767f887e89d288fea'
    VK_API_VERSION = '5.120'
    GROUP_ID = 195913773
    session = vk.Session(access_token=VK_API_ACCESS_TOKEN)
    api = vk.API(session, v=VK_API_VERSION)
    longPoll = api.groups.getLongPollServer(group_id=GROUP_ID)
    server, key, ts = longPoll['server'], longPoll['key'], longPoll['ts']


    def bass_boost(path, accentuate_db):
        def bass_line_freq(track):
            sample_track = list(track)
            # c-value
            est_mean = mean(sample_track)

            # a-value
            est_std = 3 * std(sample_track) / (math.sqrt(2))

            bass_factor = (est_std - est_mean) * 0.005

            return bass_factor

        sample = AudioSegment.from_mp3(path)

        filtered = sample.low_pass_filter(bass_line_freq(sample.get_array_of_samples()))

        combined = (sample + accentuate_db/2).overlay(filtered + accentuate_db)

        os.remove(path)

        combined.export(path, format="mp3")

    def work(update, api):
        def write_msg(message,forward_messages='',attachment=''):
            api.messages.send(user_id = update['object']['message']['from_id'],
                              random_id=randint(-2147483648, 2147483647),
                              message = message,
                              forward_messages = forward_messages,
                              attachment = attachment)
        keyboard = {
            "one_time": True,
            "buttons": [
                [
                    {
                        "action": {
                            "type": "text",
                            "payload": "{\"button\": \"2\"}",
                            "label": "Как пользоваться ботом?"
                        },
                        "color": "primary"
                    }
                ]
            ]
        }
        try:
            if update['type'] == 'message_new':
                if update['object']['message']['text'] in ['Помощь', 'Начать', 'Start','Как пользоваться ботом?']:
                    pfile = requests.post(api.photos.getMessagesUploadServer(peer_id=update['object']['message']['from_id'])['upload_url'],
                                                                    files={'photo': open('info.jpg', 'rb')}).json()

                    photo = api.photos.saveMessagesPhoto(server=pfile['server'],
                                                         photo=pfile['photo'],
                                                         hash=pfile['hash'])[0]

                    write_msg('Отправь мне список песню и напиши силу бассбуста (от 0 до 60) как на картинке ниже',
                              attachment='photo%s_%s' % (photo['owner_id'], photo['id']))
                    return


                try:
                    db = int(update['object']['message']['text'])
                    if db < 0 or db > 60:
                        raise ValueError
                    songs = [attachment for attachment in update['object']['message']['attachments'] if
                             attachment['type'] == 'audio']
                    if len(songs) == 0 or len(songs) > 1:
                        raise ValueError
                except ValueError:
                    api.messages.send(user_id=update['object']['message']['from_id'],
                                      random_id=randint(-2147483648, 2147483647),
                                      message='Неверный формат сообщения',
                                      forward_messages=update['object']['message']['id'],
                                      keyboard=json.dumps(keyboard, ensure_ascii=False))
                    return

                audio_paths = []

                write_msg('Идёт форматирование...',
                          forward_messages=update['object']['message']['id'])

                for attachment in update['object']['message']['attachments']:
                    if attachment['type'] == 'audio':
                        if attachment['audio']['duration'] > 600:
                            write_msg("Песня {} превышает лимит в 10 минут, поэтому будет пропущена".format(
                                                  attachment['audio']['title']))
                            continue
                        audio_path = attachment['audio']['title'] + '.mp3'
                        wget.download(attachment['audio']['url'], audio_path)
                        bass_boost(audio_path, db)
                        audio_paths.append(audio_path)

                for song in audio_paths:

                    afile = requests.post(api.docs.getMessagesUploadServer(peer_id=update['object']['message']['from_id'],
                                                                  type='audio_message')['upload_url'], files={'file': open(song, 'rb')}).json()['file']
                    doc = api.docs.save(file=afile)
                    write_msg("Bass Boost версия \"{}\" готова\nСсылка: {}".format(song.replace(".mp3", ""), doc['audio_message']['link_mp3']))
                    os.remove(song)
        except:
            print('thread error')
            return


    while True:
        longPoll = requests.post('%s' % server, data={'act': 'a_check',
                                                 'key': key,
                                                 'ts': ts,
                                                 'wait': 25}).json()
        try:
              if longPoll['updates']:
                 for update in longPoll['updates']:
                     threading.Thread(target=work,args=(update,api)).start()
                 ts = longPoll['ts']

        except:
             longPoll = api.groups.getLongPollServer(group_id=GROUP_ID)
             server, key, ts = longPoll['server'], longPoll['key'], longPoll['ts']
             print('longpoll restart')
             continue


if __name__ == "__main__":
    main()
    