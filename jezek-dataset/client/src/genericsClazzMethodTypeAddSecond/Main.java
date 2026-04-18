package genericsClazzMethodTypeAddSecond;

import testing_lib.genericsClazzMethodTypeAddSecond.GenericsClazzMethodTypeAddSecond;


public class Main extends GenericsClazzMethodTypeAddSecond {

	public static void main(String[] args) {

		GenericsClazzMethodTypeAddSecond constr = new GenericsClazzMethodTypeAddSecond();
		constr.<Integer>method1();
		
	}

	@Override
	public <T> void method1() {

	}

}
