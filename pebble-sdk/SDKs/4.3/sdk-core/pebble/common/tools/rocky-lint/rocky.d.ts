declare namespace rocky {
    // helper type to indicate that a commonly expected feature is planned but not implement, yet
    interface IsNotImplementedInRockyYet {
        _doesNotWork: any
    }

    interface Event {
        type: string
    }

    interface DrawEvent extends Event {
        context: CanvasRenderingContext2D
    }

    interface TickEvent extends Event {
        date: Date
    }

    interface MemoryPressureEvent extends Event {
        level: 'high';
    }

    interface MessageEvent extends Event {
        data: any;
    }

    interface PostMessageConnectionEvent extends Event {
    }

    interface AnyEvent extends Event, DrawEvent, TickEvent, MemoryPressureEvent, MessageEvent, PostMessageConnectionEvent { }

    interface CanvasRenderingContext2D {
        canvas: CanvasElement
        fillStyle: string
        font: string // TODO list actually supported fonts
        lineWidth: number
        strokeStyle: string
        textAlign: string // TODO list actually supported values
        textBaseline: IsNotImplementedInRockyYet
        arc(x: number, y: number, radius: number, startAngle: number, endAngle: number, anticlockwise?: boolean): void
        arcTo(IsNotImplementedInRockyYet : number, y1: number, x2: number, y2: number, radius: number): void
        beginPath(): void
        bezierCurveTo(cp1x: IsNotImplementedInRockyYet , cp1y: number, cp2x: number, cp2y: number, x: number, y: number): void
        clearRect(x: number, y: number, w: number, h: number): void
        closePath(): void
        drawImage(image: IsNotImplementedInRockyYet, offsetX: number, offsetY: number, width?: number, height?: number, canvasOffsetX?: number, canvasOffsetY?: number, canvasImageWidth?: number, canvasImageHeight?: number): void
        fill(fillRule?: string): void
        fillRect(x: number, y: number, w: number, h: number): void
        fillText(text: string, x: number, y: number, maxWidth?: number): void
        lineTo(x: number, y: number): void
        measureText(text: string): TextMetrics
        moveTo(x: number, y: number): void
        quadraticCurveTo(cpx: IsNotImplementedInRockyYet, cpy: number, x: number, y: number): void
        rect(x: number, y: number, w: number, h: number): void
        restore(): void
        rotate(angle: IsNotImplementedInRockyYet): void
        save(): void
        scale(x: IsNotImplementedInRockyYet , y: number): void
        setTransform(m11: IsNotImplementedInRockyYet, m12: number, m21: number, m22: number, dx: number, dy: number): void
        stroke(): void
        strokeRect(x: number, y: number, w: number, h: number): void
        transform(m11: IsNotImplementedInRockyYet, m12: number, m21: number, m22: number, dx: number, dy: number): void
        translate(x: IsNotImplementedInRockyYet , y: number): void

        rockyFillRadial(x: number, y: number, innerRadius: number, outerRadius: number, startAngle: number, endAngle: number): void
    }

    interface TextMetrics {
        width: number
        height: number
    }

    interface CanvasElement {
        clientWidth: number
        clientHeight: number
        unobstructedWidth: number
        unobstructedHeight: number
        unobstructedTop: number
        unobstructedLeft: number
    }

    interface WatchInfo {
        platform: string
        model: string
        language: string
        firmware: { major: number, minor: number, patch: number, suffix: string }
    }

    interface UserPreferences {
        contentSize: "small" | "medium" | "large" | "x-large"
    }

    interface Rocky {
        on(eventName: "draw", eventListener: (event: DrawEvent) => void): void
        on(eventName: "memorypressure", eventListener: (event: MemoryPressureEvent) => void): void
        on(eventName: "message", eventListener: (event: MessageEvent) => void): void
        on(eventName: "postmessageconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        on(eventName: "postmessagedisconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        on(eventName: "postmessageerror", eventListener: (event: MessageEvent) => void): void
        on(eventName: "hourchange", eventListener: (event: TickEvent) => void): void
        on(eventName: "minutechange", eventListener: (event: TickEvent) => void): void
        on(eventName: "secondchange", eventListener: (event: TickEvent) => void): void
        on(eventName: "daychange", eventListener: (event: TickEvent) => void): void
        on(eventName: string, eventListener: (event: AnyEvent) => void): void
        addEventListener(eventName: "draw", eventListener: (event: DrawEvent) => void): void
        addEventListener(eventName: "memorypressure", eventListener: (event: MemoryPressureEvent) => void): void
        addEventListener(eventName: "message", eventListener: (event: MessageEvent) => void): void
        addEventListener(eventName: "postmessageconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        addEventListener(eventName: "postmessagedisconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        addEventListener(eventName: "postmessageerror", eventListener: (event: MessageEvent) => void): void
        addEventListener(eventName: "hourchange", eventListener: (event: TickEvent) => void): void
        addEventListener(eventName: "minutechange", eventListener: (event: TickEvent) => void): void
        addEventListener(eventName: "secondchange", eventListener: (event: TickEvent) => void): void
        addEventListener(eventName: "daychange", eventListener: (event: TickEvent) => void): void
        addEventListener(eventName: string, eventListener: (event: AnyEvent) => void): void
        off(eventName: "draw", eventListener: (event: DrawEvent) => void): void
        off(eventName: "memorypressure", eventListener: (event: MemoryPressureEvent) => void): void
        off(eventName: "message", eventListener: (event: MessageEvent) => void): void
        off(eventName: "postmessageconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        off(eventName: "postmessagedisconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        off(eventName: "postmessageerror", eventListener: (event: MessageEvent) => void): void
        off(eventName: "hourchange", eventListener: (event: TickEvent) => void): void
        off(eventName: "minutechange", eventListener: (event: TickEvent) => void): void
        off(eventName: "secondchange", eventListener: (event: TickEvent) => void): void
        off(eventName: "daychange", eventListener: (event: TickEvent) => void): void
        off(eventName: string, eventListener: (event: AnyEvent) => void): void
        removeEventListener(eventName: "draw", eventListener: (event: DrawEvent) => void): void
        removeEventListener(eventName: "memorypressure", eventListener: (event: MemoryPressureEvent) => void): void
        removeEventListener(eventName: "message", eventListener: (event: MessageEvent) => void): void
        removeEventListener(eventName: "postmessageconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        removeEventListener(eventName: "postmessagedisconnected", eventListener: (event: PostMessageConnectionEvent) => void): void
        removeEventListener(eventName: "postmessageerror", eventListener: (event: MessageEvent) => void): void
        removeEventListener(eventName: "hourchange", eventListener: (event: TickEvent) => void): void
        removeEventListener(eventName: "minutechange", eventListener: (event: TickEvent) => void): void
        removeEventListener(eventName: "secondchange", eventListener: (event: TickEvent) => void): void
        removeEventListener(eventName: "daychange", eventListener: (event: TickEvent) => void): void
        removeEventListener(eventName: string, eventListener: (event: AnyEvent) => void): void

        postMessage(message: any): void
        requestDraw(): void
        watchInfo: WatchInfo
        userPreferences: UserPreferences
        Event: Event
        CanvasRenderingContext2D: CanvasRenderingContext2D
        CanvasElement: CanvasElement
    }
}

declare module 'rocky' {
    var rocky: rocky.Rocky;
    export = rocky
}

interface Console {
    error(message?: string, ...optionalParams: any[]): void
    log(message?: string, ...optionalParams: any[]): void
    warn(message?: string, ...optionalParams: any[]): void
}

declare var console: Console;

interface clearInterval {
    (handle: number): void
}
declare var clearInterval: clearInterval;

interface clearTimeout {
    (handle: number): void
}
declare var clearTimeout: clearTimeout;

interface setInterval {
    (handler: (...args: any[]) => void, timeout: number): number
}
declare var setInterval: setInterval;

interface setTimeout {
    (handler: (...args: any[]) => void, timeout: number): number
}
declare var setTimeout: setTimeout;

interface Require {
    (id: string): any
}

interface RockyRequire extends Require {
    (id: 'rocky'): rocky.Rocky
}

declare var require: RockyRequire;

interface Module {
    exports: any
}

declare var module: Module;
