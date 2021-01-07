import math
import os
import requests
import threading
import vk
import wget
from numpy import mean, std
from pydub import AudioSegment
from random import randint


def main():

    VK_API_ACCESS_TOKEN = 'Тут должен быть токен'
    VK_API_VERSION = '5.126'
    GROUP_ID = 195913773
    session = vk.Session(access_token=VK_API_ACCESS_TOKEN)
    api = vk.API(session, v=VK_API_VERSION)
    longPoll = api.groups.getLongPollServer(group_id=GROUP_ID)
    server, key, ts = longPoll['server'], longPoll['key'], longPoll['ts']
    active_users = []

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
        def writeMessage(message,forward_messages='',attachment=''):
            return api.messages.send(user_id = update['object']['message']['from_id'],
                                    random_id = randint(-2147483648, 2147483647),
                                    message = message,
                                    forward_messages = forward_messages,
                                    attachment = attachment)
        def editMessage(message,id,keep_forward_messages=1):
            return api.messages.edit(peer_id = update['object']['message']['from_id'],
                                message = message,
                                message_id = id,
                                keep_forward_messages = keep_forward_messages,
                                random_id = randint(-2147483648, 2147483647))
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
                messageText = update['object']['message']['text']
                print(update['object']['message']['text'])
                #Получили сообщение от пользователя
                #Если текст сообщения есть в ключевых словах, то выводим краткий туториал
                if messageText in ['Помощь', 'Начать', 'Start','Как пользоваться ботом?']:
                    pfile = requests.post(api.photos.getMessagesUploadServer(peer_id=update['object']['message']['from_id'])['upload_url'],
                                                                    files={'photo': open('info.jpg', 'rb')}).json()
                    photo = api.photos.saveMessagesPhoto(server=pfile['server'],
                                                         photo=pfile['photo'],
                                                         hash=pfile['hash'])[0]
                    writeMessage('Отправь мне песню, не превышающую по времени 10 минут, и я забастбущу её!',
                                 attachment='photo%s_%s' % (photo['owner_id'], photo['id']))
                    return
                #Иначе обрабатываем сообщение
                song = dict()
                try:
                    #Получаем список песен
                    songs = [attachment for attachment in update['object']['message']['attachments'] if
                             attachment['type'] == 'audio']
                    #Если песен больше 1 или 0 то выводим соответствующее предупреждение
                    if len(songs) == 0:
                        raise ValueError
                    elif len(songs) > 1:
                        raise IndexError
                    else:
                        song = songs[0]
                except ValueError:
                    writeMessage('Не вижу песни...',
                                  forward_messages=update['object']['message']['id'])
                    return
                except IndexError:
                    writeMessage('Слишком много песен, нужна одна', 
                                  forward_messages=update['object']['message']['id'])
                    return
                #Если песня превышает по длительности 10 минут то выводим предупреждение
                if song['audio']['duration'] > 600:
                  writeMessage("Песня {} превышает длину в 10 минут, бассбуста не будет".format(song['audio']['title']))
                  return
                #Скачиваем и бассбустим песню
                id = writeMessage('Скачиваю',
                                  forward_messages=update['object']['message']['id'])

                originalName = song['audio']['title']
                songPath = str(randint(0, 2147483647)) + '.mp3'
                wget.download(song['audio']['url'], songPath)
                editMessage("Обрабатываю",id)
                bass_boost(songPath, 15)
                
                #Выгружаем песню и отправляем итоговое сообщение пользователю
                editMessage("Выгружаю",id)
                afile = requests.post(api.docs.getMessagesUploadServer(peer_id=update['object']['message']['from_id'],
                                                                  type='audio_message')['upload_url'], files={'file': open(songPath, 'rb')}).json()['file']
                doc = api.docs.save(file=afile)
                editMessage("Bass Boost версия \"{}\" готова\nСсылка: {}".format(originalName, doc['audio_message']['link_mp3']),
                            id,
                            keep_forward_messages = 0)
                os.remove(songPath)
        except:
            writeMessage("Произошла ошибка, повторите попытку позже")
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