# Setup Tetherfi Assist Bot (TAB) Widget

Instructions to integrate the TAB widget in any web application:

### Step-1: Generate latest widget build

- Use command `npm run build` to generate build in `dist` folder

### Step-2: Copy Widget artifacts to target web project

- Copy the `tab-widget.css` and `tab-widget.iife.js` from `dist` into the target project

## Step-3: Widget Integration

- Refer `\public\index.html` for example vanilla JavaScript integration
- Refer `\setup-docs\TABWidget.txt` for example React Typescript integration component. Rename this file as `TABWidget.tsx`
