class TextFormatter:
    def shorten(text: str, length: int = 50):
        return (text[:length] + '...') if len(text) > length else text
    
    def hyperlink(text: str, url: str):
        return f"[{text}]({url})"
    
    def time(second: int):
        def pretty(n: int) -> str:
            if n < 10:
                n = f'0{n}'
            return str(n)

        sec, min, hr = second, 0, 0
        
        if sec >= 60:
            min = sec // 60
            sec = sec % 60

        if min >= 60:
            hr = min // 60
            min = min % 60

        hour = '' if hr == 0 else pretty(int(hr)) + ':'
        minute = '0:' if min == 0 else pretty(int(min)) + ':'
        second = pretty(int(sec))

        return hour + minute + second
    

class Emoji:
    play = '<:play:1060498046611374170>'
    stop = '<:stop:1060498003741397092>'
    pause = '<:pause:1042296009457414154>'

    shuffle = '<:shuffle:1042297046717190185>'
    loop_all = '<:loop_all:1060494788434079754>'
    loop_cur = '<:loop_current:1060501216557269022>'

    skip = '<:skip:1042294794044583936>'
    previous = '<:previous:1042294541539086418>'

    first = '<:beginning:1043011925790969936>'
    last = '<:last:1043011927737118730>'
    next = '<:next:1043011929477750784>'
    back = '<:back:1043011931226783845>'