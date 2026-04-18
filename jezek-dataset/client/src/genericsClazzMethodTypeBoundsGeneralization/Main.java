package genericsClazzMethodTypeBoundsGeneralization;

import testing_lib.genericsClazzMethodTypeBoundsGeneralization.GenericsClazzMethodTypeBoundsGeneralization;

public class Main extends GenericsClazzMethodTypeBoundsGeneralization {

	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsGeneralization constr = new GenericsClazzMethodTypeBoundsGeneralization();
		constr.<Integer>method1();
	}

	@Override
	public <T extends Integer> void method1() {

	}
	
}
